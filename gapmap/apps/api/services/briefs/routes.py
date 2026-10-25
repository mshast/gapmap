"""Project-brief endpoints.

``GET /api/project-plans`` is provider-free: it returns cached briefs or the
deterministic fallbacks. ``POST /api/project-plans/generate`` performs at most
one batched provider request per analysis and caches the result.
"""

from collections.abc import Awaitable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from gapmap.apps.api.contracts import GeneratePlansRequest, ProjectPlansResponse
from gapmap.apps.api.services.briefs.service import (
    PlanNotFoundError,
    ProjectPlanService,
)


router = APIRouter(prefix="/api/project-plans")
ResultT = TypeVar("ResultT")


def get_project_plan_service(request: Request) -> ProjectPlanService:
    service = getattr(request.app.state, "project_plan_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project plans are not installed.",
        )
    return service


PlanServiceDependency = Annotated[ProjectPlanService, Depends(get_project_plan_service)]


async def _public_errors(call: Awaitable[ResultT]) -> ResultT:
    try:
        return await call
    except PlanNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.public_message
        ) from None


@router.get("", response_model=ProjectPlansResponse)
async def project_plans(
    session_id: UUID,
    analysis_id: UUID,
    service: PlanServiceDependency,
) -> ProjectPlansResponse:
    return await _public_errors(service.for_analysis(session_id, analysis_id))


@router.post("/generate", response_model=ProjectPlansResponse)
async def generate_project_plans(
    request: GeneratePlansRequest,
    service: PlanServiceDependency,
) -> ProjectPlansResponse:
    return await _public_errors(service.generate(request.session_id, request.analysis_id))
