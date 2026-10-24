"""Public interview contracts and the private LLM draft schemas.

Drafts are what the model may propose. The service verifies every quote and
decides the question mix, follow-up cap, and summary in Python.
"""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from gapmap.apps.api.contracts import Identifier, StrictModel


DISCLAIMER = (
    "Practice feedback only. This is not a hiring prediction and does not change "
    "any verified skill evidence."
)
MAX_ANSWER_CHARS = 3_000
MAX_SCORE = 4

InterviewMode = Literal["llm", "demo"]
QuestionType = Literal["behavioral", "technical", "gap_probe"]
Criterion = Literal["relevance", "specificity", "structure", "impact", "accuracy"]
CRITERIA: tuple[Criterion, ...] = ("relevance", "specificity", "structure", "impact", "accuracy")

AnswerText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_ANSWER_CHARS)
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1_500)]
Quote = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
ScoreValue = Annotated[int, Field(strict=True, ge=1, le=MAX_SCORE)]


# Public contracts

class InterviewQuestion(StrictModel):
    id: Identifier
    type: QuestionType
    question: str
    requirement_id: Identifier | None
    grounding_quote: str


class StartInterviewRequest(StrictModel):
    session_id: UUID
    analysis_id: UUID


class StartInterviewResponse(StrictModel):
    interview_id: UUID
    questions: list[InterviewQuestion]
    mode: InterviewMode
    disclaimer: str = DISCLAIMER


class AnswerRequest(StrictModel):
    question_id: Identifier
    answer_text: AnswerText


class CriterionScore(StrictModel):
    criterion: Criterion
    score: ScoreValue
    max: Literal[4] = MAX_SCORE
    comment: str
    # None when the model's cited quote could not be found in the answer.
    answer_quote: str | None


class AnswerFeedback(StrictModel):
    question_id: Identifier
    scores: list[CriterionScore]
    improvements: list[str] = Field(min_length=2, max_length=3)
    suggested_rewrite: str
    follow_up: str | None
    # Answer the follow-up by posting this id to the same answer endpoint.
    follow_up_question_id: Identifier | None
    mode: InterviewMode
    disclaimer: str = DISCLAIMER


class CriterionAverage(StrictModel):
    criterion: Criterion
    average: float
    max: Literal[4] = MAX_SCORE
    answers_scored: int


class AnswerHighlight(StrictModel):
    question_id: Identifier
    question: str
    average: float


class InterviewSummary(StrictModel):
    interview_id: UUID
    answered_count: int
    total_questions: int
    criterion_averages: list[CriterionAverage]
    strongest_answer: AnswerHighlight
    weakest_answer: AnswerHighlight
    practice_suggestions: list[str] = Field(min_length=3, max_length=3)
    mode: InterviewMode
    disclaimer: str = DISCLAIMER


# Private LLM drafts. Every field is required (nullable where optional) so the
# JSON schema is valid for strict structured output.

class QuestionDraft(StrictModel):
    type: QuestionType
    question: ShortText
    requirement_id: Identifier | None
    grounding_quote: Quote


class QuestionSetDraft(StrictModel):
    questions: list[QuestionDraft] = Field(min_length=5, max_length=8)


class ScoreDraft(StrictModel):
    score: ScoreValue
    comment: ShortText
    answer_quote: Quote | None


class ScoresDraft(StrictModel):
    relevance: ScoreDraft
    specificity: ScoreDraft
    structure: ScoreDraft
    impact: ScoreDraft
    accuracy: ScoreDraft | None


class FeedbackDraft(StrictModel):
    scores: ScoresDraft
    improvements: list[ShortText] = Field(min_length=2, max_length=3)
    suggested_rewrite: LongText
    follow_up: ShortText | None


# Server-side state, never returned directly.

class InterviewRecord(StrictModel):
    id: UUID
    session_id: UUID
    analysis_id: UUID
    mode: InterviewMode
    questions: list[InterviewQuestion]
    # Follow-up question id -> the main question it follows up on.
    follow_up_parents: dict[str, str] = Field(default_factory=dict)
    answers: dict[str, AnswerFeedback] = Field(default_factory=dict)

    def question(self, question_id: str) -> InterviewQuestion | None:
        return next((item for item in self.questions if item.id == question_id), None)

    @property
    def main_question_count(self) -> int:
        return sum(1 for item in self.questions if item.id not in self.follow_up_parents)
