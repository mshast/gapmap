from gapmap.apps.api.services.projects.registry import (
    COMPETENCIES,
    COMPETENCY_WEIGHTS,
    PROJECT_ID,
    PROJECT_REGISTRY,
    TASKS,
    get_public_project,
    get_task,
)


def test_project_registry_matches_public_project() -> None:
    # Part 2's matcher reads PROJECT_REGISTRY; it must describe a project that
    # Part 3 can actually serve and grade.
    assert [template.id for template in PROJECT_REGISTRY] == [PROJECT_ID]
    for template in PROJECT_REGISTRY:
        project = get_public_project(template.id)
        assert project is not None
        assert template.title == project.title
        assert template.competencies == frozenset(project.competencies)


def test_registry_competencies_are_all_graded() -> None:
    (template,) = PROJECT_REGISTRY
    graded = {skill for task in TASKS for skill in task.points}
    assert template.competencies == graded == set(COMPETENCY_WEIGHTS) == set(COMPETENCIES)


def test_public_project_shape() -> None:
    project = get_public_project(PROJECT_ID)
    assert project is not None
    assert [task.id for task in project.tasks] == ["t1", "t2", "t3"]
    assert [task.expected_columns for task in project.tasks] == [
        ["order_id", "region", "amount_cents"],
        ["region", "gross_revenue_cents"],
        ["region", "net_revenue_cents"],
    ]
    assert sum(task.possible for task in TASKS) == 100


def test_unknown_project_and_task() -> None:
    assert get_public_project("missing") is None
    assert get_task("missing", "t1") is None
    assert get_task(PROJECT_ID, "t9") is None
