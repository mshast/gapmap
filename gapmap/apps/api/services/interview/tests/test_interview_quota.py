import json

import httpx
import pytest

from gapmap.apps.api.services.interview.llm_client import (
    DemoInterviewClient,
    InterviewLLMClient,
    InterviewRateLimited,
    client_from_env,
)
from gapmap.apps.api.services.interview.schema import InterviewQuestion
from gapmap.apps.api.services.interview.tests.fakes import completion

QUESTION = InterviewQuestion(
    id="q1", type="technical", question="Explain a LEFT JOIN.",
    requirement_id="req-sql", grounding_quote="Experience with SQL databases",
)


def start(client, ids: dict, **extra):
    return client.post("/api/interview/start", json={**ids, **extra})


def answer(client, interview_id: str, question_id: str, text: str):
    return client.post(
        f"/api/interview/{interview_id}/answer",
        json={"question_id": question_id, "answer_text": text},
    )


@pytest.mark.asyncio
async def test_quota_response_is_not_retried_and_recommends_demo_mode():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "12"}, json={"error": "quota"})

    client = InterviewLLMClient("test-only-key", transport=httpx.MockTransport(handler))
    with pytest.raises(InterviewRateLimited) as caught:
        await client.evaluate(QUESTION, "I would join the tables.", allow_follow_up=True)

    assert calls == 1
    assert caught.value.retry_after == 12
    assert "demo mode" in caught.value.public_message


def test_explicit_demo_start_uses_the_analysis_without_calling_the_provider(make_api, analyzed):
    def handler(request):
        pytest.fail("Demo mode must not call the provider")

    client, _ = make_api(InterviewLLMClient("test-only-key", transport=httpx.MockTransport(handler)))
    with client:
        response = start(client, analyzed(client), mode="demo")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "demo"
    assert len(body["questions"]) == 5
    assert all(question["grounding_quote"] for question in body["questions"])


def test_quota_on_start_falls_back_to_demo(make_api, analyzed):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "9"}, json={"error": "quota"})

    client, _ = make_api(
        InterviewLLMClient("test-only-key", transport=httpx.MockTransport(handler)),
        allow_demo_fallback=True,
    )
    with client:
        response = start(client, analyzed(client))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "demo"
    assert len(body["questions"]) == 5
    assert calls == 1


def test_quota_on_answer_switches_the_interview_to_demo(make_api, analyzed, valid_questions):
    calls: list[str] = []

    def handler(request):
        payload = json.loads(request.content)
        name = payload["response_format"]["json_schema"]["name"]
        calls.append(name)
        if name == "interview_questions":
            body = {"questions": [item.model_dump() for item in valid_questions]}
            return httpx.Response(200, json=completion(json.dumps(body)))
        return httpx.Response(429, headers={"Retry-After": "30"}, json={"error": "quota"})

    client, _ = make_api(
        InterviewLLMClient("test-only-key", transport=httpx.MockTransport(handler)),
        allow_demo_fallback=True,
    )
    with client:
        ids = analyzed(client)
        interview = start(client, ids).json()
        assert interview["mode"] == "llm"

        first = answer(
            client, interview["interview_id"], interview["questions"][0]["id"], "I joined the tables."
        )
        assert first.status_code == 200, first.text
        feedback = first.json()
        assert feedback["mode"] == "demo"
        assert all("Demo heuristic" in score["comment"] for score in feedback["scores"])

        second = answer(
            client, interview["interview_id"], interview["questions"][1]["id"], "I used a filter."
        )
        summary = client.get(f"/api/interview/{interview['interview_id']}/summary").json()

    assert second.status_code == 200
    assert second.json()["mode"] == "demo"
    assert summary["mode"] == "demo"
    # One question request and one feedback attempt; the demo answer makes no call.
    assert calls == ["interview_questions", "interview_feedback"]


def test_quota_without_fallback_is_a_clear_503(make_api, analyzed):
    def handler(request):
        return httpx.Response(429, json={"error": "quota"})

    client, _ = make_api(
        InterviewLLMClient("test-only-key", transport=httpx.MockTransport(handler)),
        allow_demo_fallback=False,
    )
    with client:
        response = start(client, analyzed(client))

    assert response.status_code == 503
    assert "out of credits or rate limited" in response.json()["detail"]


def test_interview_demo_mode_env_does_not_require_global_demo_mode(monkeypatch):
    monkeypatch.delenv("GAPMAP_DEMO_MODE", raising=False)
    monkeypatch.setenv("GAPMAP_INTERVIEW_MODE", "demo")
    monkeypatch.setenv("GAPMAP_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")

    assert isinstance(client_from_env(), DemoInterviewClient)


def test_unknown_interview_mode_is_rejected(monkeypatch):
    monkeypatch.delenv("GAPMAP_DEMO_MODE", raising=False)
    monkeypatch.setenv("GAPMAP_INTERVIEW_MODE", "sometimes")

    with pytest.raises(ValueError, match="GAPMAP_INTERVIEW_MODE"):
        client_from_env()
