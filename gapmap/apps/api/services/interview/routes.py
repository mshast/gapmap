"""Interview endpoints. Register with application.include_router(router).

Expects application.state.interview_service, an InterviewService. Errors are
mapped here so the shared error handlers do not need to change.
"""

from collections.abc import Awaitable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from gapmap.apps.api.services.interview.llm_client import InterviewUnavailableError
from gapmap.apps.api.services.interview.schema import (
    AnswerFeedback,
    AnswerRequest,
    InterviewSummary,
    StartInterviewRequest,
    StartInterviewResponse,
)
from gapmap.apps.api.services.interview.service import (
    InterviewConflictError,
    InterviewNotFoundError,
    InterviewService,
)


router = APIRouter(prefix="/api/interview")
ResultT = TypeVar("ResultT")


def get_interview_service(request: Request) -> InterviewService:
    service = getattr(request.app.state, "interview_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Interview practice is not installed."
        )
    return service


InterviewDependency = Annotated[InterviewService, Depends(get_interview_service)]


async def _public_errors(call: Awaitable[ResultT]) -> ResultT:
    try:
        return await call
    except InterviewNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.public_message) from None
    except InterviewConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.public_message) from None
    except InterviewUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.public_message
        ) from None


@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(
    request: StartInterviewRequest, service: InterviewDependency
) -> StartInterviewResponse:
    return await _public_errors(service.start(request.session_id, request.analysis_id))


@router.post("/{interview_id}/answer", response_model=AnswerFeedback)
async def answer_question(
    interview_id: UUID, request: AnswerRequest, service: InterviewDependency
) -> AnswerFeedback:
    return await _public_errors(service.answer(interview_id, request.question_id, request.answer_text))


@router.get("/{interview_id}/summary", response_model=InterviewSummary)
async def interview_summary(interview_id: UUID, service: InterviewDependency) -> InterviewSummary:
    return await _public_errors(service.summary(interview_id))
