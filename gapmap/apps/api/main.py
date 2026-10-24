"""FastAPI application factory and Uvicorn entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gapmap.apps.api.errors import install_error_handlers
from gapmap.apps.api.routes import router
from gapmap.apps.api.services.analysis import StructuredAnalysisService
from gapmap.apps.api.services.interfaces import (
    AnalysisService,
    ProjectService,
)
from gapmap.apps.api.services.projects.routes import SqlProjectService
from gapmap.apps.api.session_store import InMemorySessionStore


def create_app(
    *,
    analysis_service: AnalysisService | None = None,
    project_service: ProjectService | None = None,
    session_store: InMemorySessionStore | None = None,
) -> FastAPI:
    application = FastAPI(title="GapMap API", version="0.1.0")
    application.state.analysis_service = (
        analysis_service if analysis_service is not None else StructuredAnalysisService.from_env()
    )
    application.state.project_service = project_service or SqlProjectService()
    application.state.session_store = session_store or InMemorySessionStore()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(application)
    application.include_router(router)
    return application


app = create_app()
