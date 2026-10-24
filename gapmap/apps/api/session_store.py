"""Single-process session persistence for the hackathon foundation.

All state is lost when the API process restarts. The public interface keeps the
storage mechanism replaceable by a durable implementation later.
"""

from dataclasses import dataclass, field
from threading import RLock
from uuid import UUID, uuid4

from gapmap.apps.api.contracts import (
    AnalysisDraft,
    AnalysisResponse,
    CompetencyEvidence,
    CompetencyScore,
    EvidenceStatus,
    ProjectRecommendationResponse,
    ReadinessResponse,
    Requirement,
    SubmitResponse,
    TaskScore,
    VerificationCapability,
)
from gapmap.apps.api.services.analysis.matcher import build_roadmap
from gapmap.apps.api.services.projects.registry import competency_tasks


@dataclass
class _Session:
    analysis: AnalysisResponse
    active_submissions: dict[tuple[str, str], SubmitResponse] = field(default_factory=dict)


class InMemorySessionStore:
    """Thread-safe session storage with latest-attempt score semantics."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[UUID, _Session] = {}
        self._analysis_to_session: dict[UUID, UUID] = {}

    def create_analysis(self, draft: AnalysisDraft) -> AnalysisResponse:
        with self._lock:
            response = AnalysisResponse(
                session_id=uuid4(),
                analysis_id=uuid4(),
                **draft.model_dump(),
            )
            stored = response.model_copy(deep=True)
            self._sessions[stored.session_id] = _Session(analysis=stored)
            self._analysis_to_session[stored.analysis_id] = stored.session_id
            return response.model_copy(deep=True)

    def recommendation_for(self, analysis_id: UUID) -> ProjectRecommendationResponse | None:
        with self._lock:
            session_id = self._analysis_to_session.get(analysis_id)
            if session_id is None:
                return None
            project_id = self._sessions[session_id].analysis.recommended_project_id
            reason = (
                "Recommended because the project assesses SQL skills required by this role."
                if project_id
                else "No available project assesses the current requirements."
            )
            return ProjectRecommendationResponse(project_id=project_id, reason=reason)

    def record_submission(
        self,
        session_id: UUID,
        project_id: str,
        task_id: str,
        submission: SubmitResponse,
    ) -> bool:
        """Replace the active task attempt; return false for an unknown session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.active_submissions[(project_id, task_id)] = submission.model_copy(deep=True)
            return True

    def readiness_for(self, session_id: UUID) -> ReadinessResponse | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            evidence = self._aggregate_competencies(session)
            requirements = [
                self._recompute_requirement(item, evidence)
                for item in session.analysis.requirements
            ]
            roadmap = build_roadmap(requirements)
            earned = sum(
                attempt.task_score.earned for attempt in session.active_submissions.values()
            )
            possible = sum(
                attempt.task_score.possible for attempt in session.active_submissions.values()
            )
            return ReadinessResponse(
                session_id=session_id,
                requirements=requirements,
                competency_evidence=list(evidence.values()),
                roadmap=roadmap,
                project_total=TaskScore(earned=earned, possible=possible),
            ).model_copy(deep=True)

    @staticmethod
    def _aggregate_competencies(session: _Session) -> dict[str, CompetencyEvidence]:
        grouped: dict[str, list[tuple[str, str, CompetencyScore]]] = {}
        for (project_id, task_id), submission in session.active_submissions.items():
            for score in submission.competency_scores:
                grouped.setdefault(score.skill_id, []).append((project_id, task_id, score))

        evidence: dict[str, CompetencyEvidence] = {}
        for skill_id, entries in grouped.items():
            statuses = [entry.status for _, _, entry in entries]
            possible = 0
            complete = True
            for project_id in dict.fromkeys(project_id for project_id, _, _ in entries):
                designated = competency_tasks(project_id, skill_id)
                attempted = {task_id for source, task_id, _ in entries if source == project_id}
                complete = complete and set(designated).issubset(attempted)
                possible += sum(designated.values()) if designated else sum(
                    score.possible for source, _, score in entries if source == project_id
                )
            if complete and all(status is EvidenceStatus.DEMONSTRATED_ON_PROJECT for status in statuses):
                status = EvidenceStatus.DEMONSTRATED_ON_PROJECT
            elif any(status is not EvidenceStatus.UNVERIFIED for status in statuses):
                status = EvidenceStatus.PARTIALLY_DEMONSTRATED
            else:
                status = EvidenceStatus.UNVERIFIED
            evidence[skill_id] = CompetencyEvidence(
                skill_id=skill_id,
                status=status,
                earned=sum(entry.earned for _, _, entry in entries),
                possible=possible,
                source_project_id=entries[-1][0],
            )
        return evidence

    @staticmethod
    def _recompute_requirement(
        requirement: Requirement,
        evidence: dict[str, CompetencyEvidence],
    ) -> Requirement:
        updated = requirement.model_copy(deep=True)
        if requirement.verification_capability is VerificationCapability.NOT_ASSESSABLE:
            return updated

        uncovered = [skill_id for skill_id in requirement.skill_ids if skill_id not in evidence]
        measured = [evidence[skill_id].status for skill_id in requirement.skill_ids if skill_id in evidence]
        # Capability gaps describe skills outside the template, not skills whose
        # tests the candidate has yet to submit. Preserve the analysis disclosure.
        if (
            not uncovered
            and not requirement.uncovered_skill_ids
            and measured
            and all(status is EvidenceStatus.DEMONSTRATED_ON_PROJECT for status in measured)
        ):
            updated.evidence_status = EvidenceStatus.DEMONSTRATED_ON_PROJECT
        elif measured and any(status is not EvidenceStatus.UNVERIFIED for status in measured):
            updated.evidence_status = EvidenceStatus.PARTIALLY_DEMONSTRATED
        return updated
