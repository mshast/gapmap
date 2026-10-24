"""Safe HTTP mappings for expected service errors."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gapmap.apps.api.services.interfaces import (
    AnalysisUnavailableError,
    CapabilityUnavailableError,
)


def install_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(AnalysisUnavailableError)
    async def analysis_unavailable(
        request: Request, exc: AnalysisUnavailableError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": exc.public_message})

    @application.exception_handler(CapabilityUnavailableError)
    async def capability_unavailable(
        request: Request, exc: CapabilityUnavailableError
    ) -> JSONResponse:
        return JSONResponse(status_code=501, content={"detail": exc.public_message})
