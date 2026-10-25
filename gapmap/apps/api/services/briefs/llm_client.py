"""One batched, structured project-brief request per analysis.

Rules that keep the free tier safe: no call without a key, a conservative token
budget that falls back instead of truncating quotes, one retry only for invalid
structured output, and no retry for 429 or transport failures.
"""

import json
import logging
import os
from typing import Protocol

import httpx
from pydantic import ValidationError

from gapmap.apps.api.contracts import Requirement
from gapmap.apps.api.services.briefs.prompts import plan_messages
from gapmap.apps.api.services.briefs.schema import BriefDraft, BriefSetDraft


logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
MAX_COMPLETION_TOKENS = 3_200
# Prompt + JSON schema + completion must stay under the 8,000-token/minute tier.
MAX_REQUEST_TOKENS = 7_600
MAX_RESPONSE_BYTES = 128_000


class BriefGenerationError(Exception):
    """The project writer failed or returned unusable output. No provider bodies."""


class BriefRateLimited(BriefGenerationError):
    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__("The project writer is rate limited.")
        self.retry_after = retry_after


class BriefBudgetExceeded(BriefGenerationError):
    """The bounded request cannot fit; skip the provider and use fallbacks."""


class _InvalidOutput(Exception):
    pass


class BriefClient(Protocol):
    async def generate(
        self, target_role: str, requirements: list[Requirement]
    ) -> list[BriefDraft]: ...


class LLMBriefClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        base_url: str = "https://api.openai.com/v1/chat/completions",
        key_name: str = "OPENAI_API_KEY",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._key_name = key_name
        self._transport = transport

    async def generate(
        self, target_role: str, requirements: list[Requirement]
    ) -> list[BriefDraft]:
        if not self._api_key.strip():
            raise BriefGenerationError(
                f"No server-side project key configured. Set {self._key_name}."
            )
        messages = plan_messages(target_role, requirements)
        if not self._fits(messages):
            raise BriefBudgetExceeded("The bounded request would exceed the token budget.")
        payload = {
            "model": self._model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "project_briefs",
                    "strict": True,
                    "schema": BriefSetDraft.model_json_schema(),
                },
            },
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "store": False,
        }
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return await self._attempt(payload)
            except _InvalidOutput:
                # Log only the attempt; never the prompt or the returned text.
                logger.warning("Project brief output was invalid (attempt %d).", attempt)
                continue
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 429:
                    raise BriefRateLimited(_retry_after(error.response)) from None
                logger.warning("Project brief request failed: HTTP %d.", error.response.status_code)
                raise BriefGenerationError("The project writer failed.") from None
            except httpx.HTTPError as error:
                logger.warning("Project brief request failed: %s.", type(error).__name__)
                raise BriefGenerationError("The project writer failed.") from None
        raise BriefGenerationError("The project writer returned invalid output twice.")

    async def _attempt(self, payload: dict[str, object]) -> list[BriefDraft]:
        # The endpoint is fixed server-side; posting text cannot change it.
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            response = await client.post(
                self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise _InvalidOutput
        try:
            choice = response.json()["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict):
                raise _InvalidOutput
            if choice.get("finish_reason") != "stop" or message.get("refusal"):
                raise _InvalidOutput
            content = message["content"]
            if not isinstance(content, str):
                raise _InvalidOutput
            return BriefSetDraft.model_validate_json(content).plans
        except (ValueError, KeyError, IndexError, TypeError, ValidationError):
            # Provider bodies may echo the posting. Never expose them.
            raise _InvalidOutput from None

    @staticmethod
    def _fits(messages: list[dict[str, str]]) -> bool:
        prompt_tokens = sum(len(message["content"]) for message in messages) // 4
        schema_tokens = len(json.dumps(BriefSetDraft.model_json_schema())) // 4
        return prompt_tokens + schema_tokens + MAX_COMPLETION_TOKENS <= MAX_REQUEST_TOKENS


def _retry_after(response: httpx.Response) -> int | None:
    value = response.headers.get("retry-after")
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(seconds, 600))


def client_from_env() -> BriefClient | None:
    """Return a live client, or None when generation is not configured."""
    if os.environ.get("GAPMAP_DEMO_MODE", "").lower() in {"1", "true", "yes"}:
        return None
    provider = os.environ.get("GAPMAP_LLM_PROVIDER", "openai").strip().lower()
    if provider in {"demo", "ollama"}:
        # Ollama has no verified strict-schema path for this nested brief schema.
        return None
    if provider == "groq":
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
        key = os.environ.get("GROQ_API_KEY", "").strip()
        return LLMBriefClient(
            key,
            model,
            base_url="https://api.groq.com/openai/v1/chat/completions",
            key_name="GROQ_API_KEY",
        ) if key else None
    if provider == "openai":
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        return LLMBriefClient(key, model) if key else None
    raise ValueError(f"Unsupported GAPMAP_LLM_PROVIDER for project briefs: {provider}")
