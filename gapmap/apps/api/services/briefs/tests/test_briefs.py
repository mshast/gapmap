import asyncio
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from gapmap.apps.api.contracts import (
    AnalysisDraft,
    ReadinessResponse,
    Requirement,
    RoadmapItem,
    TaskScore,
)
from gapmap.apps.api.main import create_app
from gapmap.apps.api.services.briefs.llm_client import (
    BriefBudgetExceeded,
    BriefGenerationError,
    BriefRateLimited,
    LLMBriefClient,
)
from gapmap.apps.api.services.briefs.prompts import plan_messages
from gapmap.apps.api.services.briefs.schema import MilestoneDraft, BriefDraft
from gapmap.apps.api.services.briefs.selection import select_gaps
from gapmap.apps.api.services.briefs.service import ProjectBriefService
from gapmap.apps.api.services.demo_analysis import DemoAnalysisService
from gapmap.apps.api.session_store import InMemorySessionStore


def requirement(
    requirement_id: str = "req-python",
    label: str = "Python programming",
    quote: str = "Experience with Python is required.",
    skills: tuple[str, ...] = ("python",),
    status: str = "unverified",
    capability: str = "not_assessable",
) -> Requirement:
    return Requirement(
        id=requirement_id,
        label=label,
        job_quote=quote,
        importance=3,
        requirement_type="required",
        skill_ids=list(skills),
        evidence_status=status,
        verification_capability=capability,
    )


def milestone(index: int, tests: list[str] | None = None) -> MilestoneDraft:
    return MilestoneDraft(
        title=f"Review pass {index}",
        work=[f"Implement pass {index} input handling", f"Record pass {index} decisions"],
        acceptance_criteria=[
            f"Pass {index} handles the sample set",
            f"Pass {index} reports its totals",
        ],
        tests=tests
        or [
            f"Happy path: pass {index} returns the expected rows",
            f"Edge: pass {index} rejects a malformed row",
        ],
        evidence=f"The pass {index} output and test log.",
    )


def draft(
    requirement_id: str = "req-python",
    title: str = "Ledger Reconciliation Desk",
    tests: list[str] | None = None,
) -> BriefDraft:
    return BriefDraft(
        requirement_id=requirement_id,
        title=title,
        summary="A small tool that reconciles two exports and reports every mismatch to one analyst.",
        scenario="A finance analyst reconciles exports by hand each month and needs a repeatable run.",
        inputs=["Two CSV exports with sample rows", "A rules file naming the key columns"],
        outputs=["A reconciled CSV", "A summary with totals"],
        constraints=["Standard library only", "Deterministic output for the same inputs"],
        deliverables=["The tool and a README", "A pytest suite covering failure cases"],
        milestones=[milestone(index, tests) for index in range(1, 4)],
    )


class FakeClient:
    def __init__(self, plans=None, error=None, delay: float = 0.0) -> None:
        self.calls = 0
        self.roles: list[str] = []
        self._plans = plans
        self._error = error
        self._delay = delay

    async def generate(self, target_role: str, requirements: list[Requirement]):
        self.calls += 1
        self.roles.append(target_role)
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error
        if self._plans is not None:
            return self._plans
        return [draft(item.id) for item in requirements]


def make_api(client: FakeClient | None):
    store = InMemorySessionStore()
    service = ProjectBriefService(store, client)
    app = create_app(
        analysis_service=DemoAnalysisService(),
        session_store=store,
        project_brief_service=service,
    )
    return app, store


def analyzed(client: TestClient) -> dict:
    fixture = client.get("/api/demo/fixture").json()
    response = client.post("/api/analyze", json=fixture)
    assert response.status_code == 200
    return response.json()


def plans_url(analysis: dict) -> dict:
    return {"session_id": analysis["session_id"], "analysis_id": analysis["analysis_id"]}


def test_fallback_plans_need_no_provider() -> None:
    fake = FakeClient(error=AssertionError("the provider must not be called"))
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        response = client.get("/api/project-briefs", params=plans_url(analysis))
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert len(body["plans"]) == 4
    assert all(plan["source"] == "fallback" for plan in body["plans"])
    sql = next(plan for plan in body["plans"] if plan["runnable_project_id"])
    assert sql["runnable_project_id"] == "revenue-debug-001"
    assert sql["title"] == "Investigate an E-commerce Revenue Bug"
    assert fake.calls == 0


def test_every_fallback_has_the_full_brief_shape() -> None:
    app, _ = make_api(None)
    with TestClient(app) as client:
        analysis = analyzed(client)
        body = client.get("/api/project-briefs", params=plans_url(analysis)).json()
    for plan in body["plans"]:
        assert plan["summary"] and plan["scenario"]
        assert plan["inputs"] and plan["outputs"] and plan["constraints"]
        assert plan["deliverables"]
        assert 3 <= len(plan["milestones"]) <= 5
        for item in plan["milestones"]:
            assert 2 <= len(item["work"]) <= 3
            assert 2 <= len(item["acceptance_criteria"]) <= 4
            assert len(item["tests"]) >= 2
            assert item["evidence"]


def test_generate_once_then_serve_from_cache() -> None:
    fake = FakeClient()
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        first = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
        second = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
        read = client.get("/api/project-briefs", params=plans_url(analysis)).json()
    assert fake.calls == 1
    assert fake.roles == ["Software Engineering Intern"]
    assert first["source"] == "generated"
    assert second == first
    assert read == first
    assert all(
        plan["source"] == "generated"
        for plan in first["plans"]
        if plan["runnable_project_id"] is None
    )


def test_simultaneous_requests_share_one_provider_call() -> None:
    fake = FakeClient(delay=0.05)
    app, _ = make_api(fake)
    transport = httpx.ASGITransport(app=app)

    async def run() -> list[httpx.Response]:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            fixture = (await client.get("/api/demo/fixture")).json()
            analysis = (await client.post("/api/analyze", json=fixture)).json()
            payload = plans_url(analysis)
            return list(
                await asyncio.gather(
                    *[
                        client.post("/api/project-briefs/generate", json=payload)
                        for _ in range(3)
                    ]
                )
            )

    responses = asyncio.run(run())
    assert [response.status_code for response in responses] == [200, 200, 200]
    assert fake.calls == 1
    assert len({response.json()["plans"][0]["title"] for response in responses}) == 1


def test_mismatched_analysis_is_not_found() -> None:
    fake = FakeClient()
    app, _ = make_api(fake)
    with TestClient(app) as client:
        first = analyzed(client)
        second = analyzed(client)
        params = {"session_id": first["session_id"], "analysis_id": second["analysis_id"]}
        assert client.get("/api/project-briefs", params=params).status_code == 404
        assert client.post("/api/project-briefs/generate", json=params).status_code == 404
        unknown = {"session_id": str(uuid4()), "analysis_id": first["analysis_id"]}
        assert client.get("/api/project-briefs", params=unknown).status_code == 404
    assert fake.calls == 0


def test_selection_follows_roadmap_and_skips_ineligible_and_demonstrated() -> None:
    degree = requirement(
        "req-degree", "Degree", "Must be graduating in Spring 2028", ("other",)
    )
    demonstrated = requirement(
        "req-done", "React", "React experience", ("react",), status="demonstrated_on_project"
    )
    docker = requirement("req-b", "Docker", "Docker experience", ("docker",))
    python = requirement("req-a", "Python", "Python experience", ("python",))
    readiness = ReadinessResponse(
        session_id=uuid4(),
        requirements=[docker, degree, demonstrated, python],
        competency_evidence=[],
        roadmap=[
            RoadmapItem(requirement_id="req-degree", action="x", priority=1),
            RoadmapItem(requirement_id="req-a", action="x", priority=2),
            RoadmapItem(requirement_id="req-done", action="x", priority=3),
            RoadmapItem(requirement_id="req-b", action="x", priority=4),
        ],
        project_total=TaskScore(earned=0, possible=0),
    )
    assert [item.id for item in select_gaps(readiness)] == ["req-a", "req-b"]


def test_invented_requirement_id_is_discarded() -> None:
    fake = FakeClient(plans=[draft("req-made-up")])
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        body = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
    assert body["source"] == "fallback"
    assert all(plan["source"] == "fallback" for plan in body["plans"])
    assert fake.calls == 1


def test_technology_only_title_falls_back() -> None:
    fake = FakeClient(
        plans=[
            draft("req-react", "Build a React workflow"),
            draft("req-docker", "Build a Docker workflow"),
            draft("req-python", "Build a Python workflow"),
        ]
    )
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        body = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
    assert all(plan["source"] == "fallback" for plan in body["plans"])
    assert body["source"] == "fallback"


def test_grading_claim_is_rejected() -> None:
    fake = FakeClient(plans=[draft("req-python", tests=["Passes the hidden tests", "Edge: a row is rejected"])])
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        body = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
    assert all(plan["source"] == "fallback" for plan in body["plans"])


def test_rate_limit_is_not_retried_and_falls_back() -> None:
    fake = FakeClient(error=BriefRateLimited(30))
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        body = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
    assert fake.calls == 1
    assert body["source"] == "fallback"
    assert "30 seconds" in body["message"]
    assert all(plan["source"] == "fallback" for plan in body["plans"])


def test_budget_overflow_skips_generation() -> None:
    fake = FakeClient(error=BriefBudgetExceeded("too big"))
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        body = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
    assert body["source"] == "fallback"
    assert "too large" in body["message"]


def test_invalid_output_is_retried_once() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "not json"}, "finish_reason": "stop"}
                ]
            },
        )

    client = LLMBriefClient("test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(BriefGenerationError):
        asyncio.run(client.generate("Intern", [requirement()]))
    assert calls == 2


def test_rate_limit_status_is_not_retried_by_the_client() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            429, headers={"Retry-After": "12"}, json={"error": "rate limited"}
        )

    client = LLMBriefClient("test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(BriefRateLimited) as error:
        asyncio.run(client.generate("Intern", [requirement()]))
    assert calls == 1
    assert error.value.retry_after == 12


def test_token_budget_estimate() -> None:
    assert not LLMBriefClient._fits([{"role": "user", "content": "x" * 40_000}])
    assert LLMBriefClient._fits(plan_messages("Intern", [requirement()]))


def test_plans_do_not_change_readiness() -> None:
    fake = FakeClient()
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        before = client.get(
            "/api/readiness", params={"session_id": analysis["session_id"]}
        ).json()
        client.post("/api/project-briefs/generate", json=plans_url(analysis))
        after = client.get(
            "/api/readiness", params={"session_id": analysis["session_id"]}
        ).json()
    assert before == after


def test_prompt_omits_resume_and_interview_data() -> None:
    item = requirement()
    item.resume_quotes = ["Built a SQL reporting service at Acme Corp"]
    messages = plan_messages("Software Engineering Intern", [item])
    user_message = messages[1]["content"]
    assert item.job_quote in user_message
    assert "Acme" not in user_message
    assert "resume_quotes" not in user_message
    assert "interview" not in user_message.lower()


def test_no_eligible_gaps_returns_empty_without_a_call() -> None:
    store = InMemorySessionStore()
    analysis = store.create_analysis(
        AnalysisDraft(
            target_role="Software Engineering Intern",
            requirements=[
                requirement(
                    "req-degree", "Degree", "Must be graduating in Spring 2028", ("other",)
                )
            ],
            recommended_project_id=None,
        )
    )
    fake = FakeClient()
    service = ProjectBriefService(store, fake)
    app = create_app(
        analysis_service=DemoAnalysisService(),
        session_store=store,
        project_brief_service=service,
    )
    params = {
        "session_id": str(analysis.session_id),
        "analysis_id": str(analysis.analysis_id),
    }
    with TestClient(app) as client:
        read = client.get("/api/project-briefs", params=params).json()
        generated = client.post("/api/project-briefs/generate", json=params).json()
    assert read["plans"] == []
    assert generated["plans"] == []
    assert read["source"] == "fallback"
    assert fake.calls == 0


def test_generated_plans_reuse_stored_quotes_and_skills() -> None:
    fake = FakeClient()
    app, _ = make_api(fake)
    with TestClient(app) as client:
        analysis = analyzed(client)
        body = client.post("/api/project-briefs/generate", json=plans_url(analysis)).json()
    stored = {item["id"]: item for item in analysis["requirements"]}
    for plan in body["plans"]:
        source = stored[plan["requirement_id"]]
        assert plan["job_quote"] == source["job_quote"]
        assert set(plan["skills"]) <= set(source["skill_ids"])
        for item in plan["milestones"]:
            assert len(item["acceptance_criteria"]) >= 2
            assert len(item["tests"]) >= 2
