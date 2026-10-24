"""Ollama-backed structured extraction. Documents remain untrusted data."""

import json
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from gapmap.apps.api.services.analysis.llm_client import ExtractionError, Extractor, SYSTEM_PROMPT
from gapmap.apps.api.services.analysis.schema import ExtractionResult


class OllamaStructuredClient(Extractor):
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:3b",
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._transport = transport

    async def extract(self, resume_text: str, job_text: str) -> ExtractionResult:
        if len(resume_text) > 50_000 or len(job_text) > 50_000:
            raise ExtractionError("Document exceeds the extraction size limit.")
        delimiter = f"UNTRUSTED_DOCUMENTS_{uuid4().hex}"
        payload = {
            "model": self._model,
            "stream": False,
            "format": ExtractionResult.model_json_schema(),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"BEGIN_{delimiter}\n"
                    + json.dumps({"resume_text": resume_text, "job_text": job_text}, ensure_ascii=True)
                    + f"\nEND_{delimiter}"
                )},
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(180.0, connect=5.0),
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
            if len(response.content) > 128_000:
                raise ExtractionError("The extraction response exceeded the size limit.")
            body: Any = response.json()
            content = body["message"]["content"]
            if not isinstance(content, str):
                raise ExtractionError("The extraction response did not contain JSON text.")
            return ExtractionResult.model_validate_json(content)
        except ExtractionError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, ValidationError):
            raise ExtractionError("The Ollama provider failed or returned invalid data.") from None
