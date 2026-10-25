"""Project-brief endpoints.

``GET /api/project-briefs`` is provider-free: it returns cached briefs or the
deterministic fallbacks. ``POST /api/project-briefs/generate`` performs at most
one batched provider request per analysis and caches the result.
"""

from collections.abc import Awaitable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from gapmap.apps.api.contracts import GenerateProjectBriefsRequest, ProjectBriefsResponse
from gapmap.apps.api.services.briefs.service import (
    PlanNotFoundError,
    ProjectBriefService,
)


router = APIRouter(prefix="/api/project-briefs")
ResultT = TypeVar("ResultT")


def get_project_brief_service(request: Request) -> ProjectBriefService:
    service = getattr(request.app.state, "project_brief_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project plans are not installed.",
        )
    return service


PlanServiceDependency = Annotated[ProjectBriefService, Depends(get_project_brief_service)]


async def _public_errors(call: Awaitable[ResultT]) -> ResultT:
    try:
        return await call
    except PlanNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.public_message
        ) from None


@router.get("", response_model=ProjectBriefsResponse)
async def project_briefs(
    session_id: UUID,
    analysis_id: UUID,
    service: PlanServiceDependency,
) -> ProjectBriefsResponse:
    return await _public_errors(service.for_analysis(session_id, analysis_id))


@router.post("/generate", response_model=ProjectBriefsResponse)
async def generate_project_briefs(
    request: GenerateProjectBriefsRequest,
    service: PlanServiceDependency,
) -> ProjectBriefsResponse:
    return await _public_errors(service.generate(request.session_id, request.analysis_id))
