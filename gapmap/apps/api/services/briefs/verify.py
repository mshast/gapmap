"""Deterministic checks between a model draft and a public project plan.

The model only proposes product content. This module confirms that the draft
covers a selected requirement, names a product rather than a technology, tests
a failure case, and makes no grading claim. Everything else is copied from the
stored requirement, so quotes and skills cannot be invented.
"""

import re

from gapmap.apps.api.contracts import BriefMilestone, ProjectBrief, Requirement
from gapmap.apps.api.services.analysis.evidence import normalize_whitespace
from gapmap.apps.api.services.briefs.schema import BriefDraft


_WORD = re.compile(r"[A-Za-z0-9]+")
_AUTOMATIC_GRADING = re.compile(
    r"\b(?:auto(?:matic(?:ally)?)?[ -]?grad(?:e|ed|ing)|grader|hidden\s+tests?|"
    r"scored?\s+by\s+(?:a\s+)?grader)\b",
    re.I,
)
_EDGE_CASE = re.compile(
    r"\b(?:fail|failure|error|invalid|empty|missing|duplicate|edge|timeout|reject|"
    r"unreadable|malformed|mismatch|conflict|negative|zero|no\s+match)\w*\b",
    re.I,
)

# Verbs, articles, and technology words that make a title a topic, not a product.
_GENERIC_TITLE_TOKENS = frozenset(
    {
        "a", "an", "the", "and", "or", "of", "for", "with", "your", "using", "on",
        "in", "to", "from", "at", "by", "my", "our",
        "build", "create", "make", "write", "learn", "practice", "practise",
        "work", "complete", "improve", "strengthen", "add", "implement", "explore",
        "python", "react", "docker", "sql", "dsa", "algorithm", "algorithms",
        "workflow", "project", "app", "application", "service", "tool", "feature",
        "exercise", "assignment", "code", "coding", "programming", "cli", "script",
        "dashboard", "simple", "small", "basic", "backend", "frontend", "full",
        "stack", "demo", "portfolio", "example", "guide", "notes",
    }
)


def is_generic_title(title: str, label: str) -> bool:
    """True when the title only restates the skill or a generic deliverable."""
    if normalize_whitespace(title).casefold() == normalize_whitespace(label).casefold():
        return True
    tokens = [token.casefold() for token in _WORD.findall(title)]
    if len(tokens) < 3:
        return True
    return not (set(tokens) - _GENERIC_TITLE_TOKENS)


def _plan_text(draft: BriefDraft) -> str:
    parts = [
        draft.title, draft.summary, draft.scenario,
        *draft.inputs, *draft.outputs, *draft.constraints, *draft.deliverables,
    ]
    for milestone in draft.milestones:
        parts.extend(
            [milestone.title, *milestone.work, *milestone.acceptance_criteria,
             *milestone.tests, milestone.evidence]
        )
    return " ".join(parts)


def verify_plan(draft: BriefDraft, requirement: Requirement) -> ProjectBrief | None:
    """Return a grounded plan, or None when the draft fails a deterministic check."""
    if draft.requirement_id != requirement.id:
        return None
    if is_generic_title(draft.title, requirement.label):
        return None
    if not any(
        _EDGE_CASE.search(test)
        for milestone in draft.milestones
        for test in milestone.tests
    ):
        return None
    # Only the existing graded project may mention grading; generated plans may not.
    if _AUTOMATIC_GRADING.search(_plan_text(draft)):
        return None
    return ProjectBrief(
        id=f"plan-{requirement.id}",
        requirement_id=requirement.id,
        title=draft.title,
        summary=draft.summary,
        job_quote=requirement.job_quote,
        skills=requirement.skill_ids[:8],
        scenario=draft.scenario,
        inputs=list(draft.inputs),
        outputs=list(draft.outputs),
        constraints=list(draft.constraints),
        deliverables=list(draft.deliverables),
        milestones=[
            BriefMilestone(
                title=milestone.title,
                work=list(milestone.work),
                acceptance_criteria=list(milestone.acceptance_criteria),
                tests=list(milestone.tests),
                evidence=milestone.evidence,
            )
            for milestone in draft.milestones
        ],
        source="generated",
        runnable_project_id=None,
    )
