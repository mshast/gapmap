"""Project plans per requirement: the graded project, a reviewed skill template,
or a labeled AI suggestion for skills outside the taxonomy.

Plans are suggestions only. They never change evidence status or scores.
"""

from gapmap.apps.api.contracts import ProjectPlan, Requirement
from gapmap.apps.api.services.analysis.schema import ProjectIdea
from gapmap.apps.api.services.projects.registry import TASKS, ProjectTemplate


SKILL_LABELS = {
    "sql_joins": "SQL joins",
    "sql_filtering": "SQL filtering",
    "sql_aggregation": "SQL aggregation",
    "sql_refund_edge_cases": "Refund edge cases",
    "python": "Python",
    "react": "React",
    "docker": "Docker",
    "dsa": "Data structures",
    "java": "Java",
    "cpp": "C++",
    "csharp": "C#",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "cloud": "Cloud",
    "git": "Git",
    "apis": "APIs",
    "testing": "Testing",
    "machine_learning": "Machine learning",
    "linux": "Linux",
}

# skill -> (title, deliverable, steps)
SKILL_PLANS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "python": (
        "Build a Python workflow",
        "A tested Python tool with documented inputs, outputs, and failure cases.",
        ("Choose one real workflow from the role", "Implement the core path and validation",
         "Add tests and a short usage guide"),
    ),
    "react": (
        "Ship a React workflow",
        "A responsive React feature with loading, error, empty, and success states.",
        ("Turn the requirement into one user task", "Build accessible interactions",
         "Add responsive and interaction tests"),
    ),
    "docker": (
        "Containerize a production-shaped service",
        "A minimal container with a health check and one-command startup.",
        ("Create a small production image", "Add runtime health and configuration",
         "Document build, run, and recovery"),
    ),
    "dsa": (
        "Build an algorithm case study",
        "A benchmarked implementation that explains the data structure and complexity tradeoffs.",
        ("Define representative inputs and constraints", "Implement and test two approaches",
         "Compare complexity and measured performance"),
    ),
    "java": (
        "Build a Java REST service",
        "A small Java service with typed models, input validation, and JUnit tests.",
        ("Model one resource the team would own", "Implement create, read, and list endpoints",
         "Cover success and failure paths with JUnit"),
    ),
    "cpp": (
        "Write a performance-minded C++ tool",
        "A CMake-built C++ program with unit tests and a short benchmark write-up.",
        ("Pick a parsing or data-processing task", "Implement it with clear memory ownership",
         "Add tests and benchmark one optimization"),
    ),
    "csharp": (
        "Build a C# / .NET API",
        "An ASP.NET Core API with validation, structured errors, and xUnit tests.",
        ("Define one domain model and its rules", "Expose it through a minimal API",
         "Test the endpoints and document setup"),
    ),
    "javascript": (
        "Build a JavaScript feature end to end",
        "A Node.js or browser feature with async error handling and automated tests.",
        ("Pick one user-facing task from the role", "Implement it with clean async data flow",
         "Add tests for success, empty, and error cases"),
    ),
    "typescript": (
        "Ship a strictly typed TypeScript module",
        "A TypeScript library or API client with strict types, runtime validation, and tests.",
        ("Define the types for one real data shape", "Validate untrusted input at the boundary",
         "Publish usage examples and tests"),
    ),
    "cloud": (
        "Deploy a service to the cloud",
        "A small service running on AWS, GCP, or Azure with config, logs, and a teardown guide.",
        ("Containerize or package a small API", "Deploy it with least-privilege credentials",
         "Add logging, a health check, and cleanup steps"),
    ),
    "git": (
        "Run a project through a team Git workflow",
        "A repository with feature branches, reviewed pull requests, and a CI check.",
        ("Split one feature into small branches", "Open pull requests with clear descriptions",
         "Add a CI check that blocks failing merges"),
    ),
    "apis": (
        "Design and ship a REST API",
        "A documented REST API with validation, consistent error responses, and endpoint tests.",
        ("Write the endpoint contract first", "Implement validation and error handling",
         "Test every endpoint and publish the docs"),
    ),
    "testing": (
        "Add a real test suite to a project",
        "Unit and integration tests running in CI, plus a write-up of a bug they caught.",
        ("Pick an untested project you already have", "Cover core logic and one integration path",
         "Run the suite in CI and fix what it finds"),
    ),
    "machine_learning": (
        "Train and evaluate a small ML model",
        "A reproducible notebook or script with a baseline, evaluation metrics, and error analysis.",
        ("Choose a small public dataset tied to the role", "Compare a baseline against one model",
         "Report metrics and where the model fails"),
    ),
    "linux": (
        "Automate a task on Linux",
        "A shell script or CLI tool that automates a real workflow, with usage docs.",
        ("Pick a repetitive developer task", "Script it with safe error handling",
         "Document usage and test it on a clean machine"),
    ),
}

GENERIC_PLAN = (
    "Create a focused proof of work",
    "A reviewable artifact with a clear problem, implementation, and evidence of the result.",
    ("Translate the requirement into a concrete scenario", "Build the smallest useful artifact",
     "Document decisions, tests, and outcome"),
)


def skill_label(skill: str) -> str:
    return SKILL_LABELS.get(skill, skill.replace("_", " "))


def plans_for(
    requirement: Requirement, project: ProjectTemplate | None, idea: ProjectIdea | None = None,
) -> list[ProjectPlan]:
    if requirement.skill_ids == ["eligibility"]:
        return []
    why = f"Builds direct evidence for “{requirement.job_quote}”"
    plans = []
    graded = [skill for skill in requirement.skill_ids if project and skill in project.competencies]
    if project and graded:
        plans.append(ProjectPlan(
            id=project.id, title=project.title, skill_ids=graded, source="graded",
            why=f"Tests the {requirement.label} requirement with hidden, graded cases.",
            deliverable="A tested SQL report with correct gross and net revenue by region.",
            steps=[task.title for task in TASKS], runnable_project_id=project.id,
        ))
    # One plan per named skill; the client merges plans that share an id.
    for skill in requirement.skill_ids:
        if skill in SKILL_PLANS and skill not in graded:
            title, deliverable, steps = SKILL_PLANS[skill]
            plans.append(ProjectPlan(
                id=f"plan-{skill}", title=title, skill_ids=[skill], why=why,
                deliverable=deliverable, steps=list(steps), source="template",
            ))
    if not plans:
        if idea is not None:
            plans.append(ProjectPlan(
                id=f"plan-{requirement.id}", title=idea.title, skill_ids=requirement.skill_ids,
                why=why, deliverable=idea.deliverable, steps=idea.steps, source="ai_suggested",
            ))
        else:
            title, deliverable, steps = GENERIC_PLAN
            plans.append(ProjectPlan(
                id=f"plan-{requirement.id}", title=f"{title}: {requirement.label}",
                skill_ids=requirement.skill_ids, why=why, deliverable=deliverable,
                steps=list(steps), source="template",
            ))
    return plans
