"""FastAPI application factory and Uvicorn entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gapmap.apps.api.errors import install_error_handlers
from gapmap.apps.api.routes import router
from gapmap.apps.api.services.analysis import StructuredAnalysisService
from gapmap.apps.api.services.briefs import ProjectBriefService
from gapmap.apps.api.services.briefs.routes import router as project_briefs_router
from gapmap.apps.api.services.interfaces import (
    AnalysisService,
    ProjectService,
)
from gapmap.apps.api.services.interview.routes import router as interview_router
from gapmap.apps.api.services.interview.service import InterviewService
from gapmap.apps.api.services.projects.routes import SqlProjectService
from gapmap.apps.api.session_store import InMemorySessionStore


def create_app(
    *,
    analysis_service: AnalysisService | None = None,
    project_service: ProjectService | None = None,
    session_store: InMemorySessionStore | None = None,
    interview_service: InterviewService | None = None,
    project_brief_service: ProjectBriefService | None = None,
) -> FastAPI:
    application = FastAPI(title="GapMap API", version="0.1.0")
    application.state.analysis_service = (
        analysis_service if analysis_service is not None else StructuredAnalysisService.from_env()
    )
    application.state.project_service = project_service or SqlProjectService()
    store = session_store or InMemorySessionStore()
    application.state.session_store = store
    application.state.interview_service = interview_service or InterviewService.from_env(store)
    application.state.project_brief_service = (
        project_brief_service
        if project_brief_service is not None
        else ProjectBriefService.from_env(store)
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(application)
    application.include_router(router)
    application.include_router(interview_router)
    application.include_router(project_briefs_router)
    return application


app = create_app()
