"""Registry-only project matching and deterministic next-action priorities."""

from gapmap.apps.api.contracts import (
    EvidenceStatus, Requirement, RoadmapItem, VerificationCapability,
)
from gapmap.apps.api.services.projects.registry import PROJECT_REGISTRY, ProjectTemplate


def select_project(
    requirements: list[Requirement], registry: tuple[ProjectTemplate, ...] = PROJECT_REGISTRY
) -> ProjectTemplate | None:
    requested = {skill for requirement in requirements for skill in requirement.skill_ids}
    best = max(registry, key=lambda project: len(requested & project.competencies), default=None)
    return best if best and requested & best.competencies else None


def apply_coverage(requirement: Requirement, project: ProjectTemplate | None) -> None:
    covered = project.competencies if project else frozenset()
    requirement.uncovered_skill_ids = [skill for skill in requirement.skill_ids if skill not in covered]
    requirement.verification_capability = (
        VerificationCapability.AVAILABLE
        if set(requirement.skill_ids) & covered
        else VerificationCapability.NOT_ASSESSABLE
    )


GAP_FACTOR = {
    EvidenceStatus.UNVERIFIED: 2,
    EvidenceStatus.RESUME_EVIDENCE: 1,
    EvidenceStatus.PARTIALLY_DEMONSTRATED: 1,
    EvidenceStatus.DEMONSTRATED_ON_PROJECT: 0,
}


def build_roadmap(requirements: list[Requirement]) -> list[RoadmapItem]:
    # Python's stable sort preserves original posting order on equal priority.
    # Eligibility facts (degree, graduation date, authorization) are not skills
    # a project can build, so they never become next actions.
    ordered = sorted(
        (
            item for item in requirements
            if GAP_FACTOR[item.evidence_status] and item.skill_ids != ["eligibility"]
        ),
        key=lambda item: -(item.importance * GAP_FACTOR[item.evidence_status]),
    )
    roadmap = []
    for priority, item in enumerate(ordered, 1):
        if item.verification_capability == VerificationCapability.AVAILABLE:
            if item.evidence_status == EvidenceStatus.PARTIALLY_DEMONSTRATED:
                action = "Revisit the remaining revenue debugging tasks to build project evidence"
            else:
                action = "Complete the revenue debugging project to build SQL project evidence"
            if item.uncovered_skill_ids:
                action += "; build a separate portfolio example for " + ", ".join(item.uncovered_skill_ids)
                action += " (these skills cannot be verified by this project)"
        else:
            action = f"Build a learning or portfolio example for {item.label}; no MVP assessment is available"
        roadmap.append(RoadmapItem(requirement_id=item.id, action=action, priority=priority))
    return roadmap
