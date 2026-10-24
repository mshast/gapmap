import json

import httpx
import pytest

from gapmap.apps.api.main import create_app
from gapmap.apps.api.services.analysis.ollama_client import OllamaStructuredClient
from gapmap.apps.api.services.analysis.llm_client import ExtractionError
from gapmap.apps.api.services.analysis.schema import ExtractionResult
from gapmap.apps.api.fixtures.loader import load_demo_fixture


def valid_payload() -> dict:
    fixture = load_demo_fixture()
    quotes = [line.strip() for line in fixture.job_description.splitlines() if line.strip()][1:6]
    return {
        "target_role": "Software Engineering Intern",
        "requirements": [
            {
                "label": f"Skill {index}",
                "job_quote": quote,
                "importance": 2,
                "requirement_type": "required",
                "skill_ids": ["other"],
                "resume_quotes": [],
            }
            for index, quote in enumerate(quotes, 1)
        ],
    }


@pytest.mark.asyncio
async def test_ollama_client_posts_schema_and_parses_result() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": json.dumps(valid_payload())}})

    result = await OllamaStructuredClient(transport=httpx.MockTransport(handler)).extract("resume", "job")
    assert isinstance(result, ExtractionResult)
    assert captured["url"].endswith("/api/chat")
    assert captured["body"]["stream"] is False
    assert captured["body"]["format"]["type"] == "object"


@pytest.mark.asyncio
async def test_ollama_client_sanitizes_provider_errors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="resume secret")

    with pytest.raises(ExtractionError, match="Ollama provider failed"):
        await OllamaStructuredClient(transport=httpx.MockTransport(handler)).extract("resume", "job")


def test_ollama_provider_is_selected_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GAPMAP_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("GAPMAP_DEMO_MODE", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    app = create_app()
    assert isinstance(app.state.analysis_service._extractor, OllamaStructuredClient)


def test_groq_provider_is_selected_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GAPMAP_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    app = create_app()
    extractor = app.state.analysis_service._extractor
    assert extractor is not None
    assert extractor._base_url == "https://api.groq.com/openai/v1/chat/completions"
    assert extractor._model == "openai/gpt-oss-20b"


def test_unknown_provider_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("GAPMAP_LLM_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unsupported GAPMAP_LLM_PROVIDER"):
        create_app()
