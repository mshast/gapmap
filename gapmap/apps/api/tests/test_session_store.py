from uuid import uuid4

import pytest

from gapmap.apps.api.contracts import (
    CompetencyScore,
    EvidenceStatus,
    SubmitResponse,
    TaskScore,
)
from gapmap.apps.api.fixtures.loader import load_demo_fixture
from gapmap.apps.api.services.demo_analysis import DemoAnalysisService
from gapmap.apps.api.session_store import InMemorySessionStore


@pytest.fixture
def demo_store() -> InMemorySessionStore:
    return InMemorySessionStore()


async def demo_draft():
    fixture = load_demo_fixture()
    return await DemoAnalysisService().analyze(fixture.resume_text, fixture.job_description)


def submission(task_id: str, earned: int, possible: int, scores: list[CompetencyScore]):
    return SubmitResponse(
        submission_id=uuid4(),
        task_id=task_id,
        task_score=TaskScore(earned=earned, possible=possible),
        competency_scores=scores,
        public_test_feedback=[],
    )


def demonstrated(skill_id: str, earned: int = 10, possible: int = 10) -> CompetencyScore:
    return CompetencyScore(
        skill_id=skill_id,
        earned=earned,
        possible=possible,
        status=EvidenceStatus.DEMONSTRATED_ON_PROJECT,
    )


async def test_latest_attempt_replaces_task_score(demo_store: InMemorySessionStore) -> None:
    analysis = demo_store.create_analysis(await demo_draft())
    demo_store.record_submission(
        analysis.session_id,
        "revenue-debug-001",
        "t1",
        submission("t1", 35, 35, [demonstrated("sql_joins")]),
    )
    demo_store.record_submission(
        analysis.session_id,
        "revenue-debug-001",
        "t1",
        submission("t1", 10, 35, []),
    )
    readiness = demo_store.readiness_for(analysis.session_id)
    assert readiness is not None
    assert readiness.project_total == TaskScore(earned=10, possible=35)


async def test_sql_scores_do_not_change_unrelated_requirements(
    demo_store: InMemorySessionStore,
) -> None:
    analysis = demo_store.create_analysis(await demo_draft())
    demo_store.record_submission(
        analysis.session_id,
        "revenue-debug-001",
        "t1",
        submission("t1", 35, 35, [demonstrated("sql_joins")]),
    )
    readiness = demo_store.readiness_for(analysis.session_id)
    assert readiness is not None
    by_id = {item.id: item for item in readiness.requirements}
    assert by_id["req-react"].evidence_status == "unverified"
    assert by_id["req-docker"].evidence_status == "unverified"
    assert by_id["req-sql"].evidence_status == "partially_demonstrated"


async def test_all_sql_subskills_are_required_for_full_demonstration(
    demo_store: InMemorySessionStore,
) -> None:
    analysis = demo_store.create_analysis(await demo_draft())
    contributions = {
        "t1": [("sql_joins", 25), ("sql_filtering", 10)],
        "t2": [("sql_filtering", 10), ("sql_aggregation", 15)],
        "t3": [("sql_aggregation", 10), ("sql_refund_edge_cases", 30)],
    }
    for task_id, skills in contributions.items():
        possible = sum(points for _, points in skills)
        demo_store.record_submission(
            analysis.session_id,
            "revenue-debug-001",
            task_id,
            submission(task_id, possible, possible, [demonstrated(skill_id, points, points) for skill_id, points in skills]),
        )
    readiness = demo_store.readiness_for(analysis.session_id)
    assert readiness is not None
    sql = next(item for item in readiness.requirements if item.id == "req-sql")
    assert sql.evidence_status == "demonstrated_on_project"
    assert sql.uncovered_skill_ids == []


async def test_unknown_session_is_not_mutated(demo_store: InMemorySessionStore) -> None:
    attempt = submission("t1", 10, 10, [demonstrated("sql_joins")])
    assert not demo_store.record_submission(uuid4(), "revenue-debug-001", "t1", attempt)
    assert demo_store.readiness_for(uuid4()) is None
