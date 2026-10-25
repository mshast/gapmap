"""Server-side selection of project-eligible gaps.

The model never chooses what to work on. Selection follows the stored roadmap
priority (which already preserves posting order on ties), removes demonstrated
competencies and eligibility requirements, and caps the batch at four.
"""

import re

from gapmap.apps.api.contracts import (
    EvidenceStatus,
    ReadinessResponse,
    Requirement,
)
from gapmap.apps.api.services.projects.registry import (
    COMPETENCIES,
    PROJECT_ID,
)

MAX_PLANS = 4

# Degree, graduation date, work authorization, citizenship, visa, sponsorship.
ELIGIBILITY = re.compile(
    r"\b(?:graduat\w*|degree|class\s+of|work\s+authori[sz]ation|"
    r"authori[sz]ed\s+to\s+work|citizen(?:ship)?|legal\s+right\s+to\s+work|"
    r"visa|sponsor(?:ship)?|permanent\s+resident|green\s+card)\b",
    re.I,
)

# Deterministic fallback families, in priority order for mixed requirements.
FAMILY_ORDER = ("python", "react", "docker", "dsa")


def is_project_eligible(requirement: Requirement) -> bool:
    return (
        requirement.evidence_status is not EvidenceStatus.DEMONSTRATED_ON_PROJECT
        and not ELIGIBILITY.search(requirement.job_quote)
    )


def select_gaps(readiness: ReadinessResponse, limit: int = MAX_PLANS) -> list[Requirement]:
    """Highest-priority eligible gaps, in roadmap order."""
    by_id = {item.id: item for item in readiness.requirements}
    selected: list[Requirement] = []
    for item in readiness.roadmap:
        requirement = by_id.get(item.requirement_id)
        if requirement is None or not is_project_eligible(requirement):
            continue
        selected.append(requirement)
        if len(selected) >= limit:
            break
    return selected


def family_for(requirement: Requirement) -> str:
    skills = set(requirement.skill_ids)
    if skills & set(COMPETENCIES):
        return "sql"
    for name in FAMILY_ORDER:
        if name in skills:
            return name
    return "other"


def graded_project_id(requirement: Requirement) -> str | None:
    return PROJECT_ID if family_for(requirement) == "sql" else None
