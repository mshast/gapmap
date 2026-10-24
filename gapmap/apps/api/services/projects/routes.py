"""Part 3 project service and an optional standalone router.

``SqlProjectService`` implements the Part 4 ``ProjectService`` protocol. The
integration routes in ``gapmap/apps/api/routes.py`` already validate the
session and record graded submissions in the session store, so this service
only executes and grades; it never persists. Wire it in with::

    create_app(project_service=SqlProjectService())

``build_router`` exposes the same project endpoints for running Part 3 on its
own (e.g. local experiments). Do not mount it next to the integration router:
the paths overlap and it does not record submissions.
"""

import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from gapmap.apps.api.contracts import (
    ProjectResponse,
    RunRequest,
    RunResponse,
    SubmitRequest,
    SubmitResponse,
)
from gapmap.apps.api.services.projects.executor import execute_query
from gapmap.apps.api.services.projects.fixtures import PUBLIC_FIXTURE
from gapmap.apps.api.services.projects.grading import grade_task
from gapmap.apps.api.services.projects.registry import (
    TaskDefinition,
    get_public_project,
    get_task,
)


PREVIEW_MAX_ROWS = 20


class SqlProjectService:
    """Registry lookup, public-fixture preview, and hidden-fixture grading."""

    async def get_project(self, project_id: str) -> ProjectResponse:
        project = get_public_project(project_id)
        if project is None:
            raise _not_found("Project not found.")
        return project

    async def run(self, project_id: str, request: RunRequest) -> RunResponse:
        _require_task(project_id, request.task_id)
        result = await asyncio.to_thread(
            execute_query, request.sql, PUBLIC_FIXTURE, max_rows=PREVIEW_MAX_ROWS
        )
        return RunResponse(
            columns=result.columns,
            rows=result.rows,
            truncated=result.truncated,
            error=result.error,
        )

    async def submit(self, project_id: str, request: SubmitRequest) -> SubmitResponse:
        task = _require_task(project_id, request.task_id)
        graded = await asyncio.to_thread(grade_task, task, request.sql)
        return SubmitResponse(
            submission_id=uuid4(),
            task_id=task.id,
            task_score=graded.task_score,
            competency_scores=graded.competency_scores,
            public_test_feedback=graded.public_test_feedback,
        )


def _require_task(project_id: str, task_id: str) -> TaskDefinition:
    if get_public_project(project_id) is None:
        raise _not_found("Project not found.")
    task = get_task(project_id, task_id)
    if task is None:
        raise _not_found("Task not found.")
    return task


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def build_router(service: SqlProjectService | None = None) -> APIRouter:
    """Standalone project endpoints; see the module docstring before mounting."""
    project_service = service or SqlProjectService()
    router = APIRouter(prefix="/api")

    @router.get("/projects/{project_id}", response_model=ProjectResponse)
    async def get_project(project_id: str) -> ProjectResponse:
        return await project_service.get_project(project_id)

    @router.post("/projects/{project_id}/run", response_model=RunResponse)
    async def run_project(project_id: str, request: RunRequest) -> RunResponse:
        return await project_service.run(project_id, request)

    @router.post("/projects/{project_id}/submit", response_model=SubmitResponse)
    async def submit_project(project_id: str, request: SubmitRequest) -> SubmitResponse:
        return await project_service.submit(project_id, request)

    return router
