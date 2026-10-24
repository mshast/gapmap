from uuid import uuid4

import pytest

from gapmap.apps.api.services.analysis.evidence import verified_excerpt
from gapmap.apps.api.services.interview.llm_client import DemoInterviewClient, InterviewLLMError
from gapmap.apps.api.services.interview.prompts import GAP_PROBE_OPENING
from gapmap.apps.api.services.interview.schema import QuestionDraft
from gapmap.apps.api.services.interview.tests.fakes import FakeClient, feedback_draft
from gapmap.apps.api.services.interview.verify import sanitize_scores, verify_question


def draft(type_, requirement_id, quote, question="Tell me more about that work."):
    return QuestionDraft(type=type_, requirement_id=requirement_id, grounding_quote=quote, question=question)


def test_whitespace_variant_quote_is_accepted_in_source_form(requirements):
    verified = verify_question(draft("behavioral", "req-python", "Built a  Python\nservice that"), requirements)
    assert verified is not None
    assert verified.grounding_quote == "Built a Python service that"


@pytest.mark.parametrize("candidate", [
    draft("behavioral", "req-python", "Built a Kubernetes platform at a large company"),
    draft("behavioral", None, "Experience with SQL databases is required."),
    draft("technical", None, "Experience with SQL databases"),
    draft("technical", "req-react", "Experience with SQL databases"),
    draft("technical", "req-unknown", "Experience with SQL databases"),
    draft("technical", "req-sql", "SQL"),
    draft("gap_probe", "req-sql", "Experience with SQL databases", "You clearly lack SQL. Why?"),
    draft("gap_probe", "req-python", "Experience with Python is required.",
          f"{GAP_PROBE_OPENING} a Python data task"),
], ids=[
    "invented-resume-quote", "posting-quote-as-behavioral", "technical-without-requirement",
    "quote-from-other-requirement", "unknown-requirement", "keyword-only-quote",
    "accusing-gap-probe", "gap-probe-on-evidenced-requirement",
])
def test_unsupported_questions_are_dropped(candidate, requirements):
    assert verify_question(candidate, requirements) is None


async def test_unsupported_model_questions_are_replaced_with_grounded_ones(
    make_service, session, fixture_documents, valid_questions,
):
    _, analysis = session
    invented = [
        draft("behavioral", None, "Led a team of twenty engineers at a bank"),
        draft("technical", "req-sql", "Ten years of Oracle administration"),
    ] * 3
    client = FakeClient([invented, invented])
    started = await make_service(client).start(analysis.session_id, analysis.analysis_id)

    assert client.generate_calls == 2  # one regeneration, then grounded templates
    assert len(started.questions) == 5
    for question in started.questions:
        source = fixture_documents.resume_text if question.type == "behavioral" else fixture_documents.job_description
        assert verified_excerpt(question.grounding_quote, source) == question.grounding_quote
        assert "twenty engineers" not in question.question and "Oracle" not in question.question


async def test_regeneration_fills_the_mix_before_templates(make_service, session, valid_questions):
    _, analysis = session
    behavioral_only = [item for item in valid_questions if item.type == "behavioral"] * 3
    regenerated = [item.model_copy(update={"question": item.question + " (model)"}) for item in valid_questions]
    client = FakeClient([behavioral_only, regenerated])
    started = await make_service(client).start(analysis.session_id, analysis.analysis_id)

    assert client.generate_calls == 2
    assert all(question.question.endswith("(model)") for question in started.questions if question.type != "behavioral")


async def test_failed_regeneration_falls_back_to_grounded_templates(make_service, session):
    _, analysis = session
    client = FakeClient([[], InterviewLLMError("provider down")])
    started = await make_service(client).start(analysis.session_id, analysis.analysis_id)
    assert [question.type for question in started.questions].count("gap_probe") == 1


async def test_question_mix_is_two_behavioral_two_technical_one_gap_probe(make_service, session):
    _, analysis = session
    started = await make_service(DemoInterviewClient()).start(analysis.session_id, analysis.analysis_id)

    types = [question.type for question in started.questions]
    assert types == ["behavioral", "behavioral", "technical", "technical", "gap_probe"]
    gap = started.questions[-1]
    assert gap.question.startswith(GAP_PROBE_OPENING)
    by_id = {item.id: item for item in analysis.requirements}
    assert by_id[gap.requirement_id].evidence_status.value == "unverified"
    technical_ids = [question.requirement_id for question in started.questions[2:]]
    assert len(set(technical_ids)) == 3  # technical and gap questions cover distinct requirements


def test_unverifiable_answer_quotes_are_dropped_but_scores_kept():
    answer = "I wrote   schema checks first. Then I added tests."
    scores = sanitize_scores(feedback_draft(quote="I wrote schema checks"), answer, "technical")
    assert {item.answer_quote for item in scores} == {"I wrote   schema checks"}

    invented = sanitize_scores(feedback_draft(quote="I cut costs by 90%"), answer, "technical")
    assert all(item.answer_quote is None for item in invented)
    assert all(item.score == 3 for item in invented)


def test_accuracy_is_scored_only_for_technical_questions():
    behavioral = sanitize_scores(feedback_draft(), "An answer.", "behavioral")
    technical = sanitize_scores(feedback_draft(), "An answer.", "gap_probe")
    assert "accuracy" not in {item.criterion for item in behavioral}
    assert "accuracy" in {item.criterion for item in technical}


async def test_eligibility_requirements_are_not_interview_topics(make_service, requirements):
    eligibility = requirements[0].model_copy(update={
        "id": "req-eligibility-9", "label": "US work authorization", "skill_ids": ["eligibility"],
        "job_quote": "Must be authorized to work in the United States.",
    })

    class Source:
        def load_requirements(self, session_id, analysis_id):
            return [eligibility, *requirements]

    service = make_service(DemoInterviewClient())
    service._analysis = Source()
    started = await service.start(uuid4(), uuid4())
    assert all(question.requirement_id != "req-eligibility-9" for question in started.questions)
