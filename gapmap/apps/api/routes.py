"""Stable REST routes for GapMap integration."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from gapmap.apps.api.contracts import (
    AnalysisResponse,
    AnalyzeRequest,
    DemoFixtureResponse,
    HealthResponse,
    InputText,
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
from gapmap.apps.api.services.analysis.pdf_extract import MAX_PDF_BYTES, PDFInputError, extract_pdf_text
from gapmap.apps.api.services.demo_analysis import DemoAnalysisService
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


@router.post("/analyze/demo", response_model=AnalysisResponse)
async def analyze_demo(request: AnalyzeRequest, store: StoreDependency) -> AnalysisResponse:
    """Provider-free analysis of the bundled posting, with the supplied resume."""
    draft = await DemoAnalysisService().analyze(request.resume_text, request.job_description)
    return store.create_analysis(draft)


@router.post("/analyze/pdf", response_model=AnalysisResponse)
async def analyze_pdf(
    resume_file: Annotated[UploadFile, File(description="Text-based resume PDF, at most 5 MB; no OCR")],
    job_description: Annotated[InputText, Form()],
    analysis_service: AnalysisDependency,
    store: StoreDependency,
) -> AnalysisResponse:
    try:
        if resume_file.content_type not in {"application/pdf", "application/octet-stream"}:
            raise PDFInputError("Upload a PDF resume or paste the resume text into /api/analyze.", status_code=415)
        # Read one extra byte to detect oversize files without reading them all.
        data = await resume_file.read(MAX_PDF_BYTES + 1)
    finally:
        # Close and remove any spooled temporary upload before invoking AI.
        await resume_file.close()
    resume_text = await run_in_threadpool(extract_pdf_text, data)
    draft = await analysis_service.analyze(resume_text, job_description)
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
