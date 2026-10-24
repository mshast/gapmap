"""Service interfaces consumed by the API integration layer."""

from typing import Protocol

from gapmap.apps.api.contracts import (
    AnalysisDraft,
    ProjectResponse,
    RunRequest,
    RunResponse,
    SubmitRequest,
    SubmitResponse,
)


class PublicServiceError(Exception):
    """An expected service failure with a safe client-facing message."""

    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message


class AnalysisUnavailableError(PublicServiceError):
    """Raised when no configured analyzer can handle the input."""


class CapabilityUnavailableError(PublicServiceError):
    """Raised when an optional service has not been installed."""


class AnalysisService(Protocol):
    async def analyze(self, resume_text: str, job_description: str) -> AnalysisDraft: ...


class ProjectService(Protocol):
    async def get_project(self, project_id: str) -> ProjectResponse: ...

    async def run(self, project_id: str, request: RunRequest) -> RunResponse: ...

    async def submit(self, project_id: str, request: SubmitRequest) -> SubmitResponse: ...


class UnavailableProjectService:
    """Explicit placeholder until the Part 3 project service is integrated."""

    _MESSAGE = "Project service is not installed."

    async def get_project(self, project_id: str) -> ProjectResponse:
        raise CapabilityUnavailableError(self._MESSAGE)

    async def run(self, project_id: str, request: RunRequest) -> RunResponse:
        raise CapabilityUnavailableError(self._MESSAGE)

    async def submit(self, project_id: str, request: SubmitRequest) -> SubmitResponse:
        raise CapabilityUnavailableError(self._MESSAGE)
