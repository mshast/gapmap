"""Deterministic, fixture-scoped analysis used by the integration demo."""

from gapmap.apps.api.contracts import (
    AnalysisDraft,
    EvidenceStatus,
    Requirement,
    RequirementType,
    RoadmapItem,
    VerificationCapability,
)
from gapmap.apps.api.services.interfaces import AnalysisUnavailableError


_REQUIRED_JOB_QUOTES = (
    "Experience with SQL databases is required.",
    "Experience building user interfaces with React is preferred.",
    "Familiarity with Docker containers is preferred.",
)


class DemoAnalysisService:
    """Return grounded fixed analysis only for the canonical demo posting."""

    async def analyze(self, resume_text: str, job_description: str) -> AnalysisDraft:
        if not all(quote in job_description for quote in _REQUIRED_JOB_QUOTES):
            raise AnalysisUnavailableError(
                "General analysis is unavailable; use the demo fixture or configure the Part 2 service."
            )

        requirements = [
            Requirement(
                id="req-sql",
                label="SQL relational querying",
                job_quote=_REQUIRED_JOB_QUOTES[0],
                importance=3,
                requirement_type=RequirementType.REQUIRED,
                skill_ids=["sql_joins", "sql_filtering", "sql_aggregation"],
                resume_quotes=[],
                evidence_status=EvidenceStatus.UNVERIFIED,
                verification_capability=VerificationCapability.AVAILABLE,
            ),
            Requirement(
                id="req-react",
                label="React user interfaces",
                job_quote=_REQUIRED_JOB_QUOTES[1],
                importance=2,
                requirement_type=RequirementType.PREFERRED,
                skill_ids=["react"],
                resume_quotes=[],
                evidence_status=EvidenceStatus.UNVERIFIED,
                verification_capability=VerificationCapability.NOT_ASSESSABLE,
                uncovered_skill_ids=["react"],
            ),
            Requirement(
                id="req-docker",
                label="Docker containers",
                job_quote=_REQUIRED_JOB_QUOTES[2],
                importance=2,
                requirement_type=RequirementType.PREFERRED,
                skill_ids=["docker"],
                resume_quotes=[],
                evidence_status=EvidenceStatus.UNVERIFIED,
                verification_capability=VerificationCapability.NOT_ASSESSABLE,
                uncovered_skill_ids=["docker"],
            ),
        ]
        return AnalysisDraft(
            target_role="Software Engineering Intern",
            requirements=requirements,
            recommended_project_id="revenue-debug-001",
            roadmap=[
                RoadmapItem(
                    requirement_id="req-sql",
                    action="Complete revenue debugging project",
                    priority=1,
                ),
                RoadmapItem(
                    requirement_id="req-react",
                    action="Build a small React interface and document the decisions",
                    priority=2,
                ),
                RoadmapItem(
                    requirement_id="req-docker",
                    action="Containerize a project and document the workflow",
                    priority=3,
                ),
            ],
        )
