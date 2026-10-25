"""Canonical public contracts for the GapMap API."""

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


InputText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50_000)
]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Score = Annotated[int, Field(ge=0)]
ResultCell = int | float | str | None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceStatus(StrEnum):
    UNVERIFIED = "unverified"
    RESUME_EVIDENCE = "resume_evidence"
    PARTIALLY_DEMONSTRATED = "partially_demonstrated"
    DEMONSTRATED_ON_PROJECT = "demonstrated_on_project"


class VerificationCapability(StrEnum):
    AVAILABLE = "available"
    NOT_ASSESSABLE = "not_assessable"


class RequirementType(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class AnalyzeRequest(StrictModel):
    resume_text: InputText
    job_description: InputText


class DemoFixtureResponse(StrictModel):
    resume_text: str
    job_description: str


class ResumeEvidence(StrictModel):
    source_type: Literal["resume_claim"] = "resume_claim"
    quote: str
    strength: Literal["contextual", "keyword_only"]


class ProjectPlan(StrictModel):
    id: Identifier
    title: str
    skill_ids: list[Identifier] = Field(min_length=1)
    why: str
    deliverable: str
    steps: list[str] = Field(min_length=1)
    # graded: runnable, tested project. template: reviewed plan for a known
    # skill. ai_suggested: an idea from the model, labeled as such in the UI.
    source: Literal["graded", "template", "ai_suggested"]
    runnable_project_id: str | None = None


class Requirement(StrictModel):
    id: Identifier
    label: str
    job_quote: str
    importance: Annotated[int, Field(ge=1, le=3)]
    requirement_type: RequirementType
    skill_ids: list[Identifier] = Field(min_length=1)
    resume_quotes: list[str] = Field(default_factory=list)
    resume_evidence: list[ResumeEvidence] = Field(default_factory=list)
    evidence_status: EvidenceStatus
    verification_capability: VerificationCapability
    uncovered_skill_ids: list[Identifier] = Field(default_factory=list)
    project_plans: list[ProjectPlan] = Field(default_factory=list)


class RoadmapItem(StrictModel):
    requirement_id: Identifier
    action: str
    priority: Annotated[int, Field(ge=1)]


class AnalysisDraft(StrictModel):
    target_role: str
    requirements: list[Requirement] = Field(min_length=1)
    recommended_project_id: str | None
    roadmap: list[RoadmapItem] = Field(default_factory=list)
    analysis_mode: Literal["llm", "demo"] = "demo"
    warnings: list[str] = Field(default_factory=list)


class AnalysisResponse(AnalysisDraft):
    session_id: UUID
    analysis_id: UUID


class ProjectRecommendationResponse(StrictModel):
    project_id: str | None
    reason: str


class ProjectTask(StrictModel):
    id: Identifier
    title: str
    instructions: str
    expected_columns: list[str]
    starter_sql: str


class ProjectResponse(StrictModel):
    id: Identifier
    title: str
    scenario: str
    schema_text: str
    tasks: list[ProjectTask]
    competencies: list[Identifier]


BriefSource = Literal["generated", "fallback"]
BriefTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
BriefText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
BriefProse = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=700)]


class BriefMilestone(StrictModel):
    title: BriefTitle
    work: list[BriefText] = Field(min_length=2, max_length=3)
    acceptance_criteria: list[BriefText] = Field(min_length=2, max_length=4)
    tests: list[BriefText] = Field(min_length=2, max_length=4)
    evidence: BriefText


class ProjectBrief(StrictModel):
    id: Identifier
    requirement_id: Identifier
    title: BriefTitle
    summary: BriefProse
    job_quote: str
    skills: list[Identifier] = Field(min_length=1, max_length=8)
    scenario: BriefProse
    inputs: list[BriefText] = Field(min_length=1, max_length=6)
    outputs: list[BriefText] = Field(min_length=1, max_length=6)
    constraints: list[BriefText] = Field(min_length=1, max_length=6)
    deliverables: list[BriefText] = Field(min_length=1, max_length=6)
    milestones: list[BriefMilestone] = Field(min_length=3, max_length=5)
    source: BriefSource
    # Only the existing graded SQL project may set this.
    runnable_project_id: str | None = None


class GenerateProjectBriefsRequest(StrictModel):
    session_id: UUID
    analysis_id: UUID


class ProjectBriefsResponse(StrictModel):
    session_id: UUID
    analysis_id: UUID
    plans: list[ProjectBrief] = Field(default_factory=list, max_length=4)
    source: Literal["generated", "fallback", "mixed"]
    message: str


class RunRequest(StrictModel):
    session_id: UUID
    task_id: Identifier
    sql: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]


class RunResponse(StrictModel):
    columns: list[str]
    rows: list[list[ResultCell]]
    truncated: bool
    error: str | None


class SubmitRequest(RunRequest):
    pass


class TaskScore(StrictModel):
    earned: Score
    possible: Score


class CompetencyScore(StrictModel):
    skill_id: Identifier
    earned: Score
    possible: Score
    status: EvidenceStatus


class PublicTestFeedback(StrictModel):
    label: str
    passed: bool
    explanation: str


class SubmitResponse(StrictModel):
    submission_id: UUID
    task_id: Identifier
    task_score: TaskScore
    competency_scores: list[CompetencyScore]
    public_test_feedback: list[PublicTestFeedback]


class CompetencyEvidence(StrictModel):
    skill_id: Identifier
    status: EvidenceStatus
    earned: Score
    possible: Score
    source_project_id: Identifier


class ReadinessResponse(StrictModel):
    session_id: UUID
    requirements: list[Requirement]
    competency_evidence: list[CompetencyEvidence]
    roadmap: list[RoadmapItem]
    project_total: TaskScore


class HealthResponse(StrictModel):
    status: str
