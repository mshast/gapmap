"""Server-side checks on everything the model cites. Unverifiable quotes never reach users."""

from gapmap.apps.api.contracts import EvidenceStatus, Requirement
from gapmap.apps.api.services.analysis.evidence import verified_excerpt
from gapmap.apps.api.services.interview.prompts import GAP_PROBE_OPENING
from gapmap.apps.api.services.interview.schema import (
    CRITERIA,
    CriterionScore,
    FeedbackDraft,
    QuestionDraft,
    QuestionType,
)


# A one- or two-word "quote" is a keyword, not grounding in a specific claim.
MIN_GROUNDING_WORDS = 3


def verify_grounding(quote: str, sources: list[str]) -> str | None:
    """Return the original text of quote from the first source containing it.

    Sources are stored excerpts that analysis already verified against the
    resume or posting, so a match is also a substring of the original document.
    """
    if len(quote.split()) < MIN_GROUNDING_WORDS:
        return None
    for source in sources:
        excerpt = verified_excerpt(quote, source)
        if excerpt is not None:
            return excerpt
    return None


def verify_question(draft: QuestionDraft, requirements: list[Requirement]) -> QuestionDraft | None:
    """Return the draft with its verified quote, or None if it must be dropped."""
    by_id = {item.id: item for item in requirements}
    if draft.requirement_id is not None and draft.requirement_id not in by_id:
        return None
    scoped = [by_id[draft.requirement_id]] if draft.requirement_id else requirements
    if draft.type == "behavioral":
        # Behavioral questions must be about an experience the resume describes.
        sources = [evidence.quote for item in scoped for evidence in item.resume_evidence]
    else:
        if draft.requirement_id is None:
            return None
        sources = [item.job_quote for item in scoped]
    if draft.type == "gap_probe" and (
        by_id[draft.requirement_id].evidence_status is not EvidenceStatus.UNVERIFIED
        or not draft.question.lower().startswith(GAP_PROBE_OPENING.lower())
    ):
        return None
    quote = verify_grounding(draft.grounding_quote, sources)
    if quote is None:
        return None
    return draft.model_copy(update={"grounding_quote": quote})


def verify_answer_quote(quote: str | None, answer_text: str) -> str | None:
    if quote is None:
        return None
    return verified_excerpt(quote, answer_text)


def sanitize_scores(
    draft: FeedbackDraft, answer_text: str, question_type: QuestionType
) -> list[CriterionScore]:
    """Keep each score but drop any quote not found in the answer.

    Accuracy is scored only for technical and gap-probe questions.
    """
    scores = []
    for criterion in CRITERIA:
        item = getattr(draft.scores, criterion)
        if item is None or (criterion == "accuracy" and question_type == "behavioral"):
            continue
        scores.append(CriterionScore(
            criterion=criterion, score=item.score, comment=item.comment,
            answer_quote=verify_answer_quote(item.answer_quote, answer_text),
        ))
    return scores
