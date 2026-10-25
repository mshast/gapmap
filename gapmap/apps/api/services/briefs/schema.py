"""Private draft schemas for model-proposed project briefs.

The model proposes only the product content. The service assigns the plan id,
the stored requirement quote, the canonical skills, the source label, and the
graded-project binding; it also verifies every requirement id and title.
"""

from typing import Annotated

from pydantic import Field, StringConstraints

from gapmap.apps.api.contracts import PlanMilestone, PlanSource, PlanText, PlanTitle, PlanProse, StrictModel


RequirementId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class MilestoneDraft(StrictModel):
    title: PlanTitle
    work: list[PlanText] = Field(min_length=2, max_length=3)
    acceptance_criteria: list[PlanText] = Field(min_length=2, max_length=4)
    tests: list[PlanText] = Field(min_length=2, max_length=4)
    evidence: PlanText


class PlanDraft(StrictModel):
    requirement_id: RequirementId
    title: PlanTitle
    summary: PlanProse
    scenario: PlanProse
    inputs: list[PlanText] = Field(min_length=1, max_length=6)
    outputs: list[PlanText] = Field(min_length=1, max_length=6)
    constraints: list[PlanText] = Field(min_length=1, max_length=6)
    deliverables: list[PlanText] = Field(min_length=1, max_length=6)
    milestones: list[MilestoneDraft] = Field(min_length=3, max_length=5)


class PlanSetDraft(StrictModel):
    plans: list[PlanDraft] = Field(min_length=1, max_length=4)


# Re-exported so the service and tests agree on the public shapes.
__all__ = [
    "MilestoneDraft",
    "PlanDraft",
    "PlanSetDraft",
    "PlanMilestone",
    "PlanSource",
    "PlanText",
    "PlanTitle",
    "PlanProse",
]
