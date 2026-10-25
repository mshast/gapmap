"""Structured interview generation and feedback, with an explicitly labeled demo client."""

import asyncio
import logging
import os
import re
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from gapmap.apps.api.contracts import EvidenceStatus, Requirement
from gapmap.apps.api.services.analysis.llm_client import (
    groq_reasoning_effort, post_with_retries, schema_rejection,
)
from gapmap.apps.api.services.interfaces import PublicServiceError
from gapmap.apps.api.services.interview.prompts import (
    GAP_PROBE_OPENING,
    feedback_messages,
    question_messages,
)
from gapmap.apps.api.services.interview.schema import (
    FeedbackDraft,
    InterviewMode,
    InterviewQuestion,
    QuestionDraft,
    QuestionSetDraft,
    ScoreDraft,
    ScoresDraft,
)


logger = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=BaseModel)
MAX_ATTEMPTS = 2


class InterviewUnavailableError(PublicServiceError):
    """The interview cannot run: no key configured or the provider failed."""


class InterviewLLMError(InterviewUnavailableError):
    """The provider failed or returned invalid output twice. Never carries provider bodies."""


class InterviewRateLimited(InterviewLLMError):
    """The provider is out of credits or rate limited; demo mode can continue."""

    def __init__(self, retry_after: int | None = None) -> None:
        message = "The interview AI is out of credits or rate limited."
        if retry_after:
            message += f" Try again in {retry_after} seconds, or switch to demo mode."
        else:
            message += " Switch to demo mode to keep practicing."
        super().__init__(message)
        self.retry_after = retry_after


class _InvalidOutput(Exception):
    pass


class InterviewClient(Protocol):
    mode: InterviewMode

    async def generate_questions(self, requirements: list[Requirement]) -> list[QuestionDraft]: ...

    async def evaluate(
        self, question: InterviewQuestion, answer_text: str, *, allow_follow_up: bool
    ) -> FeedbackDraft: ...


class InterviewLLMClient:
    mode: InterviewMode = "llm"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        base_url: str = "https://api.openai.com/v1/chat/completions",
        key_name: str = "OPENAI_API_KEY",
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        reasoning_effort: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._key_name = key_name
        self._transport = transport
        self._sleep = sleep
        self._reasoning_effort = reasoning_effort

    async def generate_questions(self, requirements: list[Requirement]) -> list[QuestionDraft]:
        result = await self._complete(
            question_messages(requirements), "interview_questions", QuestionSetDraft, 3_000,
        )
        return result.questions

    async def evaluate(
        self, question: InterviewQuestion, answer_text: str, *, allow_follow_up: bool
    ) -> FeedbackDraft:
        return await self._complete(
            feedback_messages(question, answer_text, allow_follow_up=allow_follow_up),
            "interview_feedback", FeedbackDraft, 2_500,
        )

    async def _complete(
        self, messages: list[dict[str, str]], name: str, result_model: type[ModelT], max_tokens: int,
    ) -> ModelT:
        if not self._api_key.strip():
            raise InterviewUnavailableError(
                f"Interview practice is not configured. Set {self._key_name} on the server, "
                "or set GAPMAP_DEMO_MODE=1 for the labeled demo fixture."
            )
        if sum(len(message["content"]) for message in messages) > 60_000:
            raise InterviewLLMError("The interview input exceeds the size limit.")
        payload = {
            "model": self._model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": result_model.model_json_schema()},
            },
            "max_completion_tokens": max_tokens,
            "store": False,
        }
        if self._reasoning_effort:
            payload["reasoning_effort"] = self._reasoning_effort
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return await self._attempt(payload, result_model)
            except _InvalidOutput:
                # Log only the schema name and attempt; never documents or answers.
                logger.warning("Interview %s output was invalid (attempt %d).", name, attempt)
            except httpx.HTTPError as error:
                logger.warning("Interview %s request failed: %s.", name, type(error).__name__)
                break
        raise InterviewLLMError(
            "The interview AI failed or returned invalid output. Try again in a moment."
        )

    async def _attempt(self, payload: dict[str, object], result_model: type[ModelT]) -> ModelT:
        # The endpoint is fixed server-side; document URLs cannot change it.
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(45.0, connect=10.0),
            transport=self._transport, follow_redirects=False,
        ) as client:
            response = await post_with_retries(
                client, self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"}, json=payload, sleep=self._sleep,
            )
            if response.status_code in {402, 429}:
                raise InterviewRateLimited(_retry_after(response))
            if schema_rejection(response):
                # The provider rejected the model's JSON against the schema; sample again.
                raise _InvalidOutput
            response.raise_for_status()
        try:
            if len(response.content) > 128_000:
                raise _InvalidOutput
            choice = response.json()["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict):
                raise _InvalidOutput
            if choice.get("finish_reason") != "stop" or message.get("refusal"):
                raise _InvalidOutput
            content = message["content"]
            if not isinstance(content, str):
                raise _InvalidOutput
            return result_model.model_validate_json(content)
        except (ValueError, KeyError, IndexError, TypeError, ValidationError):
            # Provider bodies may echo the resume or answer. Never expose them.
            raise _InvalidOutput from None


def _retry_after(response: httpx.Response) -> int | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        seconds = int(value)
    except ValueError:
        return None
    return seconds if 0 < seconds <= 86_400 else None


def interview_mode_from_env() -> str:
    """Interview-only mode: auto (quota fallback), live (strict), or demo."""
    if os.environ.get("GAPMAP_DEMO_MODE", "").lower() in {"1", "true", "yes"}:
        return "demo"
    mode = os.environ.get("GAPMAP_INTERVIEW_MODE", "auto").strip().lower()
    if mode not in {"auto", "live", "demo"}:
        raise ValueError(f"Unsupported GAPMAP_INTERVIEW_MODE: {mode}")
    return mode


def template_questions(requirements: list[Requirement]) -> list[QuestionDraft]:
    """Deterministic, grounded candidates: every quote comes from stored, verified text."""
    behavioral: list[QuestionDraft] = []
    seen: set[str] = set()
    # Only contextual claims describe an experience; a skills-list keyword does not.
    for requirement in requirements:
        for evidence in requirement.resume_evidence:
            if evidence.strength != "contextual" or evidence.quote in seen:
                continue
            seen.add(evidence.quote)
            behavioral.append(QuestionDraft(
                type="behavioral", requirement_id=requirement.id, grounding_quote=evidence.quote,
                question=_clip(
                    f'Your resume says: "{evidence.quote.lstrip("-*• ")}" Tell me about that work: '
                    "what was the situation, what did you do, and what was the result?"
                ),
            ))
    technical = [
        QuestionDraft(
            type="technical", requirement_id=requirement.id, grounding_quote=requirement.job_quote,
            question=_clip(
                f'The posting says: "{requirement.job_quote}" Explain the key ideas behind '
                f"{requirement.label} and a mistake you would watch out for."
            ),
        )
        for requirement in sorted(requirements, key=lambda item: -item.importance)
    ]
    gap_probes = [
        QuestionDraft(
            type="gap_probe", requirement_id=requirement.id, grounding_quote=requirement.job_quote,
            question=_clip(
                f"{GAP_PROBE_OPENING} a task that needs {requirement.label}, as described in the "
                f'posting: "{requirement.job_quote}"'
            ),
        )
        for requirement in sorted(requirements, key=lambda item: -item.importance)
        if requirement.evidence_status is EvidenceStatus.UNVERIFIED
    ]
    return behavioral + technical + gap_probes


def _clip(text: str, limit: int = 400) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


_SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")
_STRUCTURE_CUES = re.compile(
    r"\b(when|situation|task|goal|needed|so I|I (?:built|wrote|led|designed|fixed|added|used)|"
    r"first|then|next|because|finally|as a result|result)\b",
    re.I,
)
_IMPACT_CUES = re.compile(r"\d|%|\b(reduced|increased|improved|saved|faster|fewer|cut|grew)\b", re.I)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "what", "how",
    "you", "your", "did", "that", "this", "is", "was", "me", "about", "tell", "would",
}
_DEMO_IMPROVEMENTS = {
    "relevance": "Open by answering the exact question in one sentence before adding background.",
    "specificity": "Name the specific tools, data, and decisions you made instead of general claims.",
    "structure": "Use a clear order: situation, task, the actions you took, then the result.",
    "impact": "End with a concrete outcome, and a number if you measured one.",
}


class DemoInterviewClient:
    """Offline, deterministic fixture. Every response is labeled mode='demo'."""

    mode: InterviewMode = "demo"

    async def generate_questions(self, requirements: list[Requirement]) -> list[QuestionDraft]:
        return template_questions(requirements)

    async def evaluate(
        self, question: InterviewQuestion, answer_text: str, *, allow_follow_up: bool
    ) -> FeedbackDraft:
        sentences = [match.group().strip() for match in _SENTENCE.finditer(answer_text) if match.group().strip()]
        words = answer_text.split()
        question_terms = {
            term for term in re.findall(r"[a-z]+", question.question.lower()) if term not in _STOPWORDS
        }
        overlap = question_terms.intersection(re.findall(r"[a-z]+", answer_text.lower()))
        structure_hits = len(_STRUCTURE_CUES.findall(answer_text))
        impact_sentence = next((item for item in sentences if _IMPACT_CUES.search(item)), None)
        scores = {
            "relevance": _band(len(overlap), (1, 3, 5)),
            "specificity": _band(len(words), (25, 60, 120)),
            "structure": _band(structure_hits, (1, 3, 5)),
            "impact": _band(len(_IMPACT_CUES.findall(answer_text)), (1, 2, 4)),
        }
        quotes = {
            "relevance": _short(sentences[0]) if sentences else None,
            "specificity": _short(max(sentences, key=len)) if sentences else None,
            "structure": _short(next((item for item in sentences if _STRUCTURE_CUES.search(item)), "")),
            "impact": _short(impact_sentence or ""),
        }
        weakest = sorted(scores, key=lambda key: scores[key])
        rewrite_source = quotes[weakest[0]] or (sentences[0] if sentences else answer_text)
        return FeedbackDraft(
            scores=ScoresDraft(
                **{
                    key: ScoreDraft(
                        score=scores[key],
                        comment=f"Demo heuristic: {key} scored {scores[key]} of 4 from simple text signals.",
                        answer_quote=quotes[key],
                    )
                    for key in scores
                },
                # The demo cannot judge technical correctness, so it does not pretend to.
                accuracy=None,
            ),
            improvements=[_DEMO_IMPROVEMENTS[key] for key in weakest[:2]],
            suggested_rewrite=_clip(
                f"{rewrite_source} [Add what you did next and the result you observed.]", 1_500
            ),
            follow_up=(
                "What changed as a result of that work, and how did you know?"
                if allow_follow_up and scores["impact"] <= 2 else None
            ),
        )


def _band(value: int, thresholds: tuple[int, int, int]) -> int:
    return 1 + sum(value >= threshold for threshold in thresholds)


def _short(sentence: str, max_words: int = 25, max_chars: int = 400) -> str | None:
    # Cut a prefix of the original text so the quote stays verbatim.
    if not sentence:
        return None
    matches = list(re.finditer(r"\S+", sentence))
    if len(matches) > max_words:
        sentence = sentence[: matches[max_words - 1].end()]
    return sentence[:max_chars].rstrip()


def client_from_env() -> InterviewClient:
    """Demo when explicitly enabled; otherwise the live client, which errors without a key."""
    if interview_mode_from_env() == "demo":
        return DemoInterviewClient()
    provider = os.environ.get("GAPMAP_LLM_PROVIDER", "openai").strip().lower()
    if provider == "demo":
        return DemoInterviewClient()
    if provider == "groq":
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
        return InterviewLLMClient(
            os.environ.get("GROQ_API_KEY", "").strip(),
            model,
            base_url="https://api.groq.com/openai/v1/chat/completions",
            key_name="GROQ_API_KEY",
            reasoning_effort=groq_reasoning_effort(model),
        )
    if provider == "openai":
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        return InterviewLLMClient(os.environ.get("OPENAI_API_KEY", "").strip(), model)
    if provider == "ollama":
        # shortcut: interviews need hosted structured output; add Ollama only if its schema support is verified.
        return InterviewLLMClient("", key_name="GROQ_API_KEY or OPENAI_API_KEY")
    raise ValueError(f"Unsupported GAPMAP_LLM_PROVIDER for interviews: {provider}")
