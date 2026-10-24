"""Interview start, answer, and summary logic.

The model proposes questions and feedback. Python verifies every quote and
decides the question mix, the follow-up cap, and the summary.
"""

from uuid import UUID, uuid4

from gapmap.apps.api.contracts import Requirement
from gapmap.apps.api.services.analysis.evidence import normalize_whitespace
from gapmap.apps.api.services.interfaces import PublicServiceError
from gapmap.apps.api.services.interview.llm_client import (
    InterviewClient,
    InterviewLLMError,
    client_from_env,
    template_questions,
)
from gapmap.apps.api.services.interview.schema import (
    CRITERIA,
    AnswerFeedback,
    AnswerHighlight,
    AnswerRequest,
    CriterionAverage,
    InterviewQuestion,
    InterviewRecord,
    InterviewSummary,
    QuestionDraft,
    StartInterviewResponse,
)
from gapmap.apps.api.services.interview.store import (
    AnalysisSource,
    InMemoryInterviewStore,
    InterviewStore,
    SessionStoreAnalysisSource,
)
from gapmap.apps.api.services.interview.verify import sanitize_scores, verify_question
from gapmap.apps.api.session_store import InMemorySessionStore


QUESTION_COUNT = 5
_PRACTICE = {
    "relevance": "Answer the exact question in your first sentence, then add supporting detail.",
    "specificity": "Name the specific tools, data, and decisions you made instead of general claims.",
    "structure": (
        "Tell stories as situation, task, action, result, and explain technical answers step by step."
    ),
    "impact": "Close each answer with a concrete outcome, and a number when you measured one.",
    "accuracy": "Review the core concepts behind the technical questions and explain one trade-off for each.",
}


class InterviewNotFoundError(PublicServiceError):
    """Unknown session, analysis, interview, or question."""


class InterviewConflictError(PublicServiceError):
    """The request conflicts with the interview's current state."""


class InterviewService:
    def __init__(
        self, client: InterviewClient, store: InterviewStore, analysis_source: AnalysisSource,
    ) -> None:
        self._client = client
        self._store = store
        self._analysis = analysis_source

    @classmethod
    def from_env(cls, session_store: InMemorySessionStore) -> "InterviewService":
        return cls(client_from_env(), InMemoryInterviewStore(), SessionStoreAnalysisSource(session_store))

    async def start(self, session_id: UUID, analysis_id: UUID) -> StartInterviewResponse:
        requirements = self._analysis.load_requirements(session_id, analysis_id)
        if not requirements:
            raise InterviewNotFoundError("Analysis not found for this session.")
        candidates = await self._verified_candidates(requirements)
        questions = [
            InterviewQuestion(id=f"q{index}", **draft.model_dump())
            for index, draft in enumerate(select_questions(candidates), start=1)
        ]
        record = InterviewRecord(
            id=uuid4(), session_id=session_id, analysis_id=analysis_id,
            mode=self._client.mode, questions=questions,
        )
        self._store.save_interview(record)
        return StartInterviewResponse(interview_id=record.id, questions=questions, mode=record.mode)

    async def _verified_candidates(self, requirements: list[Requirement]) -> list[QuestionDraft]:
        # A failure on the first call is a clear error, never a silent fixture.
        proposed = await self._client.generate_questions(requirements)
        verified = _verify_all(proposed, requirements)
        if not _mix_satisfied(verified):
            try:
                verified += _verify_all(await self._client.generate_questions(requirements), requirements)
            except InterviewLLMError:
                pass
        # Model questions come first; grounded templates only fill remaining gaps.
        return verified + template_questions(requirements)

    async def answer(self, interview_id: UUID, question_id: str, answer_text: str) -> AnswerFeedback:
        # Validate even direct Python callers: stripped, non-empty, at most 3000 chars.
        request = AnswerRequest(question_id=question_id, answer_text=answer_text)
        record = self._load(interview_id)
        question = record.question(request.question_id)
        if question is None:
            raise InterviewNotFoundError("Question not found in this interview.")
        _ensure_unanswered(record, question.id)
        allow_follow_up = question.id not in record.follow_up_parents
        draft = await self._client.evaluate(question, request.answer_text, allow_follow_up=allow_follow_up)

        # Reload after the provider call so a concurrent answer cannot be overwritten.
        record = self._load(interview_id)
        _ensure_unanswered(record, question.id)
        follow_up = draft.follow_up if allow_follow_up else None
        follow_up_id = None
        if follow_up is not None:
            follow_up_id = f"{question.id}-followup"
            record.questions.append(question.model_copy(update={"id": follow_up_id, "question": follow_up}))
            record.follow_up_parents[follow_up_id] = question.id
        feedback = AnswerFeedback(
            question_id=question.id,
            scores=sanitize_scores(draft, request.answer_text, question.type),
            improvements=draft.improvements,
            suggested_rewrite=draft.suggested_rewrite,
            follow_up=follow_up,
            follow_up_question_id=follow_up_id,
            mode=record.mode,
        )
        record.answers[question.id] = feedback
        self._store.save_interview(record)
        return feedback

    async def summary(self, interview_id: UUID) -> InterviewSummary:
        record = self._load(interview_id)
        if not record.answers:
            raise InterviewConflictError("Answer at least one question before requesting a summary.")
        averages = []
        for criterion in CRITERIA:
            values = [
                score.score for feedback in record.answers.values()
                for score in feedback.scores if score.criterion == criterion
            ]
            if values:
                averages.append(CriterionAverage(
                    criterion=criterion, average=round(sum(values) / len(values), 2),
                    answers_scored=len(values),
                ))
        # Ties resolve to the earlier question, in interview order.
        highlights = [
            AnswerHighlight(
                question_id=question.id, question=question.question,
                average=round(_mean([item.score for item in record.answers[question.id].scores]), 2),
            )
            for question in record.questions if question.id in record.answers
        ]
        strongest = max(highlights, key=lambda item: item.average)
        weakest = min(highlights, key=lambda item: item.average)
        lowest = sorted(averages, key=lambda item: item.average)[:2]
        suggestions = [
            f"{item.criterion.capitalize()} (average {item.average:.1f} of 4): {_PRACTICE[item.criterion]}"
            for item in lowest
        ]
        suggestions.append(
            f"Re-answer your weakest question ({weakest.question_id}) out loud, applying its "
            "improvements and suggested rewrite."
        )
        return InterviewSummary(
            interview_id=record.id, answered_count=len(record.answers),
            total_questions=len(record.questions), criterion_averages=averages,
            strongest_answer=strongest, weakest_answer=weakest,
            practice_suggestions=suggestions, mode=record.mode,
        )

    def _load(self, interview_id: UUID) -> InterviewRecord:
        record = self._store.load_interview(interview_id)
        if record is None:
            raise InterviewNotFoundError("Interview not found.")
        return record


def select_questions(candidates: list[QuestionDraft]) -> list[QuestionDraft]:
    """Pick 2 behavioral, 2 technical, and 1 gap probe, in candidate order.

    Shortfalls are filled with other technical questions, then behavioral ones.
    """
    selected: list[QuestionDraft] = []
    quotes: set[str] = set()
    used_requirements: set[str] = set()
    texts: set[str] = set()

    def take(question_type: str, count: int) -> None:
        for draft in candidates:
            if sum(item.type == question_type for item in selected) >= count:
                return
            # Technical and gap-probe questions each cover a different requirement.
            if (
                draft.type != question_type
                or normalize_whitespace(draft.question).lower() in texts
                or (question_type == "behavioral" and draft.grounding_quote in quotes)
                or (question_type != "behavioral" and draft.requirement_id in used_requirements)
            ):
                continue
            selected.append(draft)
            texts.add(normalize_whitespace(draft.question).lower())
            quotes.add(draft.grounding_quote)
            if question_type != "behavioral" and draft.requirement_id:
                used_requirements.add(draft.requirement_id)

    take("gap_probe", 1)
    take("behavioral", 2)
    take("technical", 2)
    take("technical", QUESTION_COUNT - len(selected) + _count(selected, "technical"))
    take("behavioral", QUESTION_COUNT - len(selected) + _count(selected, "behavioral"))
    order = {"behavioral": 0, "technical": 1, "gap_probe": 2}
    return sorted(selected, key=lambda item: order[item.type])


def _verify_all(drafts: list[QuestionDraft], requirements: list[Requirement]) -> list[QuestionDraft]:
    return [item for item in (verify_question(draft, requirements) for draft in drafts) if item is not None]


def _mix_satisfied(drafts: list[QuestionDraft]) -> bool:
    selected = select_questions(drafts)
    return all(
        _count(selected, kind) == need
        for kind, need in (("behavioral", 2), ("technical", 2), ("gap_probe", 1))
    )


def _count(drafts: list[QuestionDraft], question_type: str) -> int:
    return sum(item.type == question_type for item in drafts)


def _mean(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _ensure_unanswered(record: InterviewRecord, question_id: str) -> None:
    if question_id in record.answers:
        raise InterviewConflictError("This question has already been answered.")
