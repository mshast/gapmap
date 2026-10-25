"""Private draft schemas for model-proposed project briefs.

The model proposes only the product content. The service assigns the plan id,
the stored requirement quote, the canonical skills, the source label, and the
graded-project binding; it also verifies every requirement id and title.
"""

from typing import Annotated

from pydantic import Field, StringConstraints

from gapmap.apps.api.contracts import BriefMilestone, BriefSource, BriefText, BriefTitle, BriefProse, StrictModel


RequirementId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class MilestoneDraft(StrictModel):
    title: BriefTitle
    work: list[BriefText] = Field(min_length=2, max_length=3)
    acceptance_criteria: list[BriefText] = Field(min_length=2, max_length=4)
    tests: list[BriefText] = Field(min_length=2, max_length=4)
    evidence: BriefText


class BriefDraft(StrictModel):
    requirement_id: RequirementId
    title: BriefTitle
    summary: BriefProse
    scenario: BriefProse
    inputs: list[BriefText] = Field(min_length=1, max_length=6)
    outputs: list[BriefText] = Field(min_length=1, max_length=6)
    constraints: list[BriefText] = Field(min_length=1, max_length=6)
    deliverables: list[BriefText] = Field(min_length=1, max_length=6)
    milestones: list[MilestoneDraft] = Field(min_length=3, max_length=5)


class BriefSetDraft(StrictModel):
    plans: list[BriefDraft] = Field(min_length=1, max_length=4)


# Re-exported so the service and tests agree on the public shapes.
__all__ = [
    "MilestoneDraft",
    "BriefDraft",
    "BriefSetDraft",
    "BriefMilestone",
    "BriefSource",
    "BriefText",
    "BriefTitle",
    "BriefProse",
]
