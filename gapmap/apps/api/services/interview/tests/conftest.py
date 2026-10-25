import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gapmap.apps.api.contracts import AnalysisResponse
from gapmap.apps.api.fixtures.loader import load_demo_fixture
from gapmap.apps.api.main import create_app
from gapmap.apps.api.services.analysis import StructuredAnalysisService
from gapmap.apps.api.services.interview.llm_client import template_questions
from gapmap.apps.api.services.interview.schema import QuestionDraft
from gapmap.apps.api.services.interview.service import InterviewService
from gapmap.apps.api.services.interview.store import InMemoryInterviewStore, SessionStoreAnalysisSource
from gapmap.apps.api.services.interview.tests.fakes import completion, feedback_draft
from gapmap.apps.api.session_store import InMemorySessionStore


@pytest.fixture
def fixture_documents():
    return load_demo_fixture()


@pytest.fixture
async def session(fixture_documents) -> tuple[InMemorySessionStore, AnalysisResponse]:
    store = InMemorySessionStore()
    draft = await StructuredAnalysisService(demo_mode=True).analyze(
        fixture_documents.resume_text, fixture_documents.job_description
    )
    return store, store.create_analysis(draft)


@pytest.fixture
def requirements(session):
    return session[1].requirements


@pytest.fixture
def valid_questions(requirements) -> list[QuestionDraft]:
    # 2 behavioral, 5 technical, then the first gap probe: a satisfiable mix.
    return template_questions(requirements)[:8]


@pytest.fixture
def make_service(session):
    store, _ = session

    def build(client) -> InterviewService:
        return InterviewService(client, InMemoryInterviewStore(), SessionStoreAnalysisSource(store))

    return build


@pytest.fixture
def make_api():
    """The shared app with this router mounted, as the integration hand-off describes."""

    def build(interview_client, *, allow_demo_fallback: bool = False) -> tuple[TestClient, FastAPI]:
        store = InMemorySessionStore()
        service = InterviewService(
            interview_client, InMemoryInterviewStore(),
            SessionStoreAnalysisSource(store),
            allow_demo_fallback=allow_demo_fallback,
        )
        app = create_app(
            analysis_service=StructuredAnalysisService(demo_mode=True),
            session_store=store,
            interview_service=service,
        )
        return TestClient(app), app

    return build


@pytest.fixture
def analyzed():
    """Run the demo analysis through the API and return its ids."""

    def run(client: TestClient) -> dict:
        documents = client.get("/api/demo/fixture").json()
        response = client.post("/api/analyze", json={
            "resume_text": documents["resume_text"], "job_description": documents["job_description"],
        })
        assert response.status_code == 200
        body = response.json()
        return {"session_id": body["session_id"], "analysis_id": body["analysis_id"]}

    return run


@pytest.fixture
def provider_handler(valid_questions):
    """An OpenAI-shaped mock that answers by schema name and records payloads."""

    def build(feedback_contents: list[str] | None = None):
        payloads: list[dict] = []
        feedback = list(feedback_contents or [feedback_draft().model_dump_json()])

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            payloads.append(payload)
            if payload["response_format"]["json_schema"]["name"] == "interview_questions":
                body = {"questions": [item.model_dump() for item in valid_questions]}
                return httpx.Response(200, json=completion(json.dumps(body)))
            content = feedback.pop(0) if len(feedback) > 1 else feedback[0]
            return httpx.Response(200, json=completion(content))

        return handler, payloads

    return build
