"""FastAPI dependencies backed by application state."""

from fastapi import Request

from gapmap.apps.api.services.interfaces import AnalysisService, ProjectService
from gapmap.apps.api.session_store import InMemorySessionStore


def get_analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


def get_project_service(request: Request) -> ProjectService:
    return request.app.state.project_service


def get_session_store(request: Request) -> InMemorySessionStore:
    return request.app.state.session_store
