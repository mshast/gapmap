"""Interview persistence stub until the shared session store supports interviews.

The interview module only reads analysis data. It never writes requirement or
competency evidence, which belongs to the deterministic project grader.
"""

from threading import RLock
from typing import Protocol
from uuid import UUID

from gapmap.apps.api.contracts import Requirement
from gapmap.apps.api.services.interview.schema import InterviewRecord
from gapmap.apps.api.session_store import InMemorySessionStore


class InterviewStore(Protocol):
    def save_interview(self, record: InterviewRecord) -> None: ...

    def load_interview(self, interview_id: UUID) -> InterviewRecord | None: ...


class AnalysisSource(Protocol):
    def load_requirements(self, session_id: UUID, analysis_id: UUID) -> list[Requirement] | None: ...


class InMemoryInterviewStore:
    """Single-process storage; all interviews are lost when the API restarts."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._interviews: dict[UUID, InterviewRecord] = {}

    def save_interview(self, record: InterviewRecord) -> None:
        with self._lock:
            self._interviews[record.id] = record.model_copy(deep=True)

    def load_interview(self, interview_id: UUID) -> InterviewRecord | None:
        with self._lock:
            record = self._interviews.get(interview_id)
            return record.model_copy(deep=True) if record is not None else None


class SessionStoreAnalysisSource:
    """Read-only adapter over the shared session store's public methods.

    Limitation: the public API cannot confirm that analysis_id belongs to
    session_id; it only confirms both exist. A session-store method that checks
    ownership should replace this adapter.
    """

    def __init__(self, session_store: InMemorySessionStore) -> None:
        self._session_store = session_store

    def load_requirements(self, session_id: UUID, analysis_id: UUID) -> list[Requirement] | None:
        if self._session_store.recommendation_for(analysis_id) is None:
            return None
        # Readiness includes project results, so gap probes skip skills already
        # demonstrated on the work sample.
        readiness = self._session_store.readiness_for(session_id)
        return readiness.requirements if readiness is not None else None
