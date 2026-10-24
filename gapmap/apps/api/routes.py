"""Stable REST routes for GapMap integration."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from gapmap.apps.api.contracts import (
    AnalysisResponse,
    AnalyzeRequest,
    DemoFixtureResponse,
    HealthResponse,
    ProjectRecommendationResponse,
    ProjectResponse,
    ReadinessResponse,
    RunRequest,
    RunResponse,
    SubmitRequest,
    SubmitResponse,
)
from gapmap.apps.api.dependencies import (
    get_analysis_service,
    get_project_service,
    get_session_store,
)
from gapmap.apps.api.fixtures.loader import load_demo_fixture
from gapmap.apps.api.services.interfaces import AnalysisService, ProjectService
from gapmap.apps.api.session_store import InMemorySessionStore


router = APIRouter(prefix="/api")
AnalysisDependency = Annotated[AnalysisService, Depends(get_analysis_service)]
ProjectDependency = Annotated[ProjectService, Depends(get_project_service)]
StoreDependency = Annotated[InMemorySessionStore, Depends(get_session_store)]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/demo/fixture", response_model=DemoFixtureResponse)
async def demo_fixture() -> DemoFixtureResponse:
    return load_demo_fixture()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    request: AnalyzeRequest,
    analysis_service: AnalysisDependency,
    store: StoreDependency,
) -> AnalysisResponse:
    draft = await analysis_service.analyze(request.resume_text, request.job_description)
    return store.create_analysis(draft)


@router.get("/projects/recommended", response_model=ProjectRecommendationResponse)
async def recommended_project(
    analysis_id: UUID,
    store: StoreDependency,
) -> ProjectRecommendationResponse:
    recommendation = store.recommendation_for(analysis_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    return recommendation


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, project_service: ProjectDependency) -> ProjectResponse:
    return await project_service.get_project(project_id)


@router.post("/projects/{project_id}/run", response_model=RunResponse)
async def run_project(
    project_id: str,
    request: RunRequest,
    project_service: ProjectDependency,
    store: StoreDependency,
) -> RunResponse:
    if store.readiness_for(request.session_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return await project_service.run(project_id, request)


@router.post("/projects/{project_id}/submit", response_model=SubmitResponse)
async def submit_project(
    project_id: str,
    request: SubmitRequest,
    project_service: ProjectDependency,
    store: StoreDependency,
) -> SubmitResponse:
    if store.readiness_for(request.session_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    result = await project_service.submit(project_id, request)
    store.record_submission(request.session_id, project_id, request.task_id, result)
    return result


@router.get("/readiness", response_model=ReadinessResponse)
async def readiness(session_id: UUID, store: StoreDependency) -> ReadinessResponse:
    result = store.readiness_for(session_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return result
