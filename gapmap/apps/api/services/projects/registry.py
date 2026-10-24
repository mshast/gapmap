"""The fixed competency registry shared with the Part 3 SQL workstream.

Metadata only: registering a template does not install its executor or grader.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectTemplate:
    id: str
    title: str
    competencies: frozenset[str]


PROJECT_REGISTRY = (
    ProjectTemplate(
        id="revenue-debug-001",
        title="Investigate an E-commerce Revenue Bug",
        competencies=frozenset(
            {"sql_joins", "sql_filtering", "sql_aggregation", "sql_refund_edge_cases"}
        ),
    ),
)
