import json
import logging

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gapmap.apps.api.services.interview.llm_client import (
    DemoInterviewClient,
    InterviewLLMClient,
    client_from_env,
)
from gapmap.apps.api.services.interview.routes import router
from gapmap.apps.api.services.interview.schema import DISCLAIMER
from gapmap.apps.api.services.interview.tests.fakes import FakeClient, feedback_draft


UNKNOWN = "00000000-0000-0000-0000-000000000000"


def start(client: TestClient, ids: dict) -> dict:
    response = client.post("/api/interview/start", json=ids)
    assert response.status_code == 200, response.text
    return response.json()


def answer(client: TestClient, interview_id: str, question_id: str, text: str):
    return client.post(
        f"/api/interview/{interview_id}/answer", json={"question_id": question_id, "answer_text": text}
    )


@pytest.mark.parametrize("text", ["", "   \n\t "], ids=["empty", "whitespace"])
def test_empty_answer_is_rejected(make_api, analyzed, text):
    client, _ = make_api(DemoInterviewClient())
    with client:
        interview = start(client, analyzed(client))
        assert answer(client, interview["interview_id"], "q1", text).status_code == 422


def test_oversized_answer_is_rejected_and_limit_is_inclusive(make_api, analyzed):
    client, _ = make_api(DemoInterviewClient())
    with client:
        interview = start(client, analyzed(client))
        assert answer(client, interview["interview_id"], "q1", "x" * 3_001).status_code == 422
        assert answer(client, interview["interview_id"], "q1", "x" * 3_000).status_code == 200


def test_invalid_llm_output_is_retried_once(make_api, analyzed, provider_handler):
    handler, payloads = provider_handler(["not json", feedback_draft().model_dump_json()])
    client, _ = make_api(InterviewLLMClient("test-only-key", transport=httpx.MockTransport(handler)))
    with client:
        interview = start(client, analyzed(client))
        response = answer(client, interview["interview_id"], "q1", "I built a validation service.")
    assert response.status_code == 200
    feedback_calls = [p for p in payloads if p["response_format"]["json_schema"]["name"] == "interview_feedback"]
    assert len(feedback_calls) == 2
    assert response.json()["mode"] == "llm"


def test_invalid_llm_output_twice_is_a_clear_sanitized_error(make_api, analyzed, provider_handler, caplog):
    handler, payloads = provider_handler(["private-answer-echo"])
    client, _ = make_api(InterviewLLMClient("test-only-key", transport=httpx.MockTransport(handler)))
    secret_answer = "My private answer mentions project Falcon."
    with client, caplog.at_level(logging.DEBUG):
        interview = start(client, analyzed(client))
        response = answer(client, interview["interview_id"], "q1", secret_answer)
        # The failed answer is not recorded, so the question can be retried.
        retry_state = client.get(f"/api/interview/{interview['interview_id']}/summary")

    assert response.status_code == 503
    assert "failed or returned invalid output" in response.json()["detail"]
    assert "private-answer-echo" not in response.text
    assert len([p for p in payloads if p["response_format"]["json_schema"]["name"] == "interview_feedback"]) == 2
    assert retry_state.status_code == 409
    assert "Falcon" not in caplog.text and "private-answer-echo" not in caplog.text


def test_missing_api_key_is_a_clear_error_and_never_calls_the_provider(make_api, analyzed):
    def handler(request):
        pytest.fail("The provider must not be called without a key")

    client, _ = make_api(InterviewLLMClient("", transport=httpx.MockTransport(handler)))
    with client:
        response = client.post("/api/interview/start", json=analyzed(client))
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_environment_selects_demo_only_when_enabled(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GAPMAP_DEMO_MODE", raising=False)
    assert isinstance(client_from_env(), InterviewLLMClient)  # errors on use, never silent demo
    monkeypatch.setenv("GAPMAP_DEMO_MODE", "1")
    assert isinstance(client_from_env(), DemoInterviewClient)


def test_demo_mode_is_labeled_everywhere(make_api, analyzed):
    client, _ = make_api(DemoInterviewClient())
    with client:
        interview = start(client, analyzed(client))
        feedback = answer(client, interview["interview_id"], "q1", "I built it.").json()
        summary = client.get(f"/api/interview/{interview['interview_id']}/summary").json()
    for body in (interview, feedback, summary):
        assert body["mode"] == "demo"
        assert body["disclaimer"] == DISCLAIMER
    assert all("Demo heuristic" in score["comment"] for score in feedback["scores"])


def test_one_follow_up_per_question(make_api, analyzed, valid_questions):
    fake = FakeClient([valid_questions], feedback_draft(follow_up="What was the measured result?"))
    client, _ = make_api(fake)
    with client:
        interview = start(client, analyzed(client))
        first = answer(client, interview["interview_id"], "q1", "I built it.").json()
        follow = answer(client, interview["interview_id"], first["follow_up_question_id"], "It helped.").json()

    assert first["follow_up"] == "What was the measured result?"
    assert first["follow_up_question_id"] == "q1-followup"
    assert follow["follow_up"] is None and follow["follow_up_question_id"] is None
    assert fake.allow_follow_up == [True, False]


def test_summary_averages_highlights_and_suggestions(make_api, analyzed, valid_questions):
    fake = FakeClient([valid_questions])
    client, _ = make_api(fake)
    with client:
        interview = start(client, analyzed(client))
        interview_id = interview["interview_id"]
        fake.feedback = feedback_draft(score=4, accuracy=False)
        answer(client, interview_id, "q1", "Strong answer.")
        fake.feedback = feedback_draft(score=1)
        answer(client, interview_id, "q3", "Weak answer.")
        summary = client.get(f"/api/interview/{interview_id}/summary").json()

    averages = {item["criterion"]: item for item in summary["criterion_averages"]}
    assert averages["relevance"]["average"] == 2.5 and averages["relevance"]["answers_scored"] == 2
    assert averages["accuracy"]["average"] == 1.0 and averages["accuracy"]["answers_scored"] == 1
    assert summary["strongest_answer"]["question_id"] == "q1"
    assert summary["weakest_answer"]["question_id"] == "q3"
    assert len(summary["practice_suggestions"]) == 3
    assert summary["practice_suggestions"][0].startswith("Accuracy (average 1.0 of 4)")
    assert "(q3)" in summary["practice_suggestions"][2]
    assert "percent" not in json.dumps(summary).lower()


def test_interview_never_changes_verified_evidence(make_api, analyzed, valid_questions):
    client, _ = make_api(FakeClient([valid_questions], feedback_draft(score=4)))
    with client:
        ids = analyzed(client)
        before = client.get("/api/readiness", params={"session_id": ids["session_id"]}).json()
        interview = start(client, ids)
        for question in interview["questions"]:
            assert answer(client, interview["interview_id"], question["id"], "Perfect answer.").status_code == 200
        after = client.get("/api/readiness", params={"session_id": ids["session_id"]}).json()
    assert after == before


def test_state_and_lookup_errors(make_api, analyzed):
    client, _ = make_api(DemoInterviewClient())
    with client:
        ids = analyzed(client)
        assert client.post("/api/interview/start", json={**ids, "session_id": UNKNOWN}).status_code == 404
        assert client.post("/api/interview/start", json={**ids, "analysis_id": UNKNOWN}).status_code == 404
        interview = start(client, ids)
        interview_id = interview["interview_id"]
        assert client.get(f"/api/interview/{interview_id}/summary").status_code == 409
        assert answer(client, interview_id, "q99", "An answer.").status_code == 404
        assert answer(client, UNKNOWN, "q1", "An answer.").status_code == 404
        assert answer(client, interview_id, "q1", "An answer.").status_code == 200
        assert answer(client, interview_id, "q1", "Again.").status_code == 409
        assert client.get(f"/api/interview/{UNKNOWN}/summary").status_code == 404


def test_router_without_service_reports_not_installed():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        assert client.get(f"/api/interview/{UNKNOWN}/summary").status_code == 501


def test_default_app_mounts_interview_routes(monkeypatch):
    monkeypatch.setenv("GAPMAP_DEMO_MODE", "1")
    from gapmap.apps.api.main import create_app

    with TestClient(create_app()) as client:
        documents = client.get("/api/demo/fixture").json()
        analysis = client.post("/api/analyze", json={
            "resume_text": documents["resume_text"], "job_description": documents["job_description"],
        }).json()
        response = client.post("/api/interview/start", json={
            "session_id": analysis["session_id"], "analysis_id": analysis["analysis_id"],
        })
    assert response.status_code == 200
    assert response.json()["mode"] == "demo"


def test_groq_provider_uses_the_groq_endpoint(monkeypatch):
    monkeypatch.delenv("GAPMAP_DEMO_MODE", raising=False)
    monkeypatch.setenv("GAPMAP_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    client = client_from_env()
    assert isinstance(client, InterviewLLMClient)
    assert client._base_url == "https://api.groq.com/openai/v1/chat/completions"
