"""Batched project briefs with cache-first reads and single-flight generation.

One analysis costs at most one provider request. Cached briefs are served on
every later read. A failure never poisons the cache and never destroys the
deterministic fallback cards.
"""

import asyncio
import threading
from dataclasses import dataclass
from typing import Awaitable, Callable
from uuid import UUID

from gapmap.apps.api.contracts import (
    ProjectPlan,
    ProjectPlansResponse,
    Requirement,
)
from gapmap.apps.api.services.briefs.fallback import fallback_plan
from gapmap.apps.api.services.briefs.llm_client import (
    BriefBudgetExceeded,
    BriefClient,
    BriefGenerationError,
    BriefRateLimited,
    client_from_env,
)
from gapmap.apps.api.services.briefs.selection import family_for, select_gaps
from gapmap.apps.api.services.briefs.verify import verify_plan
from gapmap.apps.api.services.interfaces import PublicServiceError
from gapmap.apps.api.session_store import InMemorySessionStore


FALLBACK_MESSAGE = (
    "Deterministic project templates. Generate tailored projects to adapt them "
    "to this posting."
)
NO_GAPS_MESSAGE = "No project-eligible gaps remain for this analysis."
NOT_CONFIGURED_MESSAGE = (
    "Project generation is not configured on the server. Showing deterministic projects."
)
FAILURE_MESSAGE = (
    "The project writer is unavailable right now. Showing deterministic projects; "
    "try again in a moment."
)
BUDGET_MESSAGE = (
    "This posting is too large for one bounded project request. Showing deterministic projects."
)
NO_USABLE_MESSAGE = (
    "The project writer returned no usable briefs. Showing deterministic projects."
)
SQL_ONLY_MESSAGE = (
    "The graded SQL project is the available assessment for these gaps. "
    "No other project-eligible gaps remain."
)


class PlanNotFoundError(PublicServiceError):
    """Unknown session, analysis, or a mismatched pair."""


@dataclass(frozen=True)
class _Context:
    session_id: UUID
    analysis_id: UUID
    role: str
    gaps: list[Requirement]


class _SingleFlight:
    """Run one generation task per (loop, session, analysis) pair."""

    def __init__(self) -> None:
        self._tasks: dict[tuple[int, UUID, UUID], asyncio.Task[ProjectPlansResponse]] = {}
        self._lock = threading.Lock()

    async def run(
        self,
        key: tuple[UUID, UUID],
        factory: Callable[[], Awaitable[ProjectPlansResponse]],
    ) -> ProjectPlansResponse:
        loop = asyncio.get_running_loop()
        full_key = (id(loop), key[0], key[1])
        with self._lock:
            task = self._tasks.get(full_key)
            if task is None or task.done():
                task = loop.create_task(factory())
                self._tasks[full_key] = task
        try:
            # Shield the shared task so one cancelled waiter cannot cancel it.
            return await asyncio.shield(task)
        finally:
            with self._lock:
                if self._tasks.get(full_key) is task and task.done():
                    self._tasks.pop(full_key, None)


class ProjectPlanService:
    def __init__(
        self,
        store: InMemorySessionStore,
        client: BriefClient | None,
        *,
        flight: _SingleFlight | None = None,
    ) -> None:
        self._store = store
        self._client = client
        self._flight = flight or _SingleFlight()

    @classmethod
    def from_env(cls, store: InMemorySessionStore) -> "ProjectPlanService":
        return cls(store, client_from_env())

    async def for_analysis(self, session_id: UUID, analysis_id: UUID) -> ProjectPlansResponse:
        """Cached briefs when present, otherwise deterministic fallbacks. No provider call."""
        context = self._context(session_id, analysis_id)
        cached = self._store.load_plans(session_id, analysis_id)
        if cached is not None:
            return cached
        if not context.gaps:
            return self._empty(context)
        return self._response(
            context,
            [fallback_plan(gap) for gap in context.gaps],
            "fallback",
            FALLBACK_MESSAGE,
        )

    async def generate(self, session_id: UUID, analysis_id: UUID) -> ProjectPlansResponse:
        """One batched generation per analysis; cached results are reused."""
        context = self._context(session_id, analysis_id)
        cached = self._store.load_plans(session_id, analysis_id)
        if cached is not None:
            return cached
        if not context.gaps:
            return self._empty(context)
        response = await self._flight.run(
            (session_id, analysis_id), lambda: self._generate(context)
        )
        # Cache only a complete result. A partial or failed run is left uncached
        # so an explicit retry can attempt the missing briefs again.
        if response.source == "generated":
            self._store.store_plans(session_id, analysis_id, response)
        return response

    async def _generate(self, context: _Context) -> ProjectPlansResponse:
        # A simultaneous request may have finished while this one queued.
        cached = self._store.load_plans(context.session_id, context.analysis_id)
        if cached is not None:
            return cached

        targets = [gap for gap in context.gaps if family_for(gap) != "sql"]
        drafts = []
        warning = ""
        if targets:
            if self._client is None:
                warning = NOT_CONFIGURED_MESSAGE
            else:
                try:
                    drafts = await self._client.generate(context.role, targets)
                except BriefBudgetExceeded:
                    warning = BUDGET_MESSAGE
                except BriefRateLimited as error:
                    warning = _rate_message(error.retry_after)
                except BriefGenerationError:
                    warning = FAILURE_MESSAGE

        by_requirement = {}
        for draft in drafts:
            # First plan per requirement wins; duplicates are ignored.
            by_requirement.setdefault(draft.requirement_id, draft)

        plans: list[ProjectPlan] = []
        for gap in context.gaps:
            if family_for(gap) == "sql":
                plans.append(fallback_plan(gap))
                continue
            draft = by_requirement.get(gap.id)
            verified = verify_plan(draft, gap) if draft is not None else None
            plans.append(verified or fallback_plan(gap))

        generated = sum(1 for plan in plans if plan.source == "generated")
        if not targets:
            return self._response(context, plans, "fallback", SQL_ONLY_MESSAGE)
        if generated == len(targets):
            return self._response(context, plans, "generated", "Tailored from this posting.")
        if generated:
            return self._response(
                context,
                plans,
                "mixed",
                f"Tailored {generated} of {len(targets)} projects; the rest use the "
                "deterministic template.",
            )
        return self._response(context, plans, "fallback", warning or NO_USABLE_MESSAGE)

    def _context(self, session_id: UUID, analysis_id: UUID) -> _Context:
        requirements = self._store.requirements_for(session_id, analysis_id)
        if requirements is None:
            raise PlanNotFoundError("Analysis not found for this session.")
        readiness = self._store.readiness_for(session_id)
        if readiness is None:
            raise PlanNotFoundError("Analysis not found for this session.")
        return _Context(
            session_id=session_id,
            analysis_id=analysis_id,
            role=self._store.target_role_for(session_id, analysis_id) or "this role",
            gaps=select_gaps(readiness),
        )

    @staticmethod
    def _empty(context: _Context) -> ProjectPlansResponse:
        return ProjectPlansResponse(
            session_id=context.session_id,
            analysis_id=context.analysis_id,
            plans=[],
            source="fallback",
            message=NO_GAPS_MESSAGE,
        )

    @staticmethod
    def _response(
        context: _Context,
        plans: list[ProjectPlan],
        source: str,
        message: str,
    ) -> ProjectPlansResponse:
        return ProjectPlansResponse(
            session_id=context.session_id,
            analysis_id=context.analysis_id,
            plans=plans,
            source=source,
            message=message,
        )


def _rate_message(retry_after: int | None) -> str:
    base = "The project writer is rate limited. Showing deterministic projects"
    if retry_after:
        return f"{base}; try again in {retry_after} seconds."
    return f"{base}; try again in a moment."
