"""Public project metadata, competency IDs, and fixed point allocations.

Nothing in this module is secret: it is exactly what the client may see, plus
the per-task point weights. Hidden fixtures and oracle answers live elsewhere.
"""

from dataclasses import dataclass

from gapmap.apps.api.contracts import ProjectResponse, ProjectTask


PROJECT_ID = "revenue-debug-001"
PROJECT_TITLE = "Investigate an E-commerce Revenue Bug"

SQL_JOINS = "sql_joins"
SQL_FILTERING = "sql_filtering"
SQL_AGGREGATION = "sql_aggregation"
SQL_REFUND_EDGE_CASES = "sql_refund_edge_cases"
COMPETENCIES = (SQL_JOINS, SQL_FILTERING, SQL_AGGREGATION, SQL_REFUND_EDGE_CASES)

# Fixed spec 03 weighting: joins 25, filtering 20, aggregation 25, refunds 30.
COMPETENCY_WEIGHTS = {
    SQL_JOINS: 25,
    SQL_FILTERING: 20,
    SQL_AGGREGATION: 25,
    SQL_REFUND_EDGE_CASES: 30,
}

UNKNOWN_REGION = "Unknown"

SCENARIO = (
    "Finance reports that the regional revenue dashboard disagrees with the "
    "ledger. The dashboard query counts every order regardless of status and "
    "joins refunds in a way that may count some orders more than once. Trace "
    "valid orders to their regions, recompute gross revenue, then correct net "
    "revenue after refunds."
)

SCHEMA_TEXT = """\
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, region TEXT);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER,
  amount_cents INTEGER,
  status TEXT,        -- 'completed', 'pending', or 'cancelled'
  created_at TEXT     -- ISO-8601 date
);
CREATE TABLE refunds (id INTEGER PRIMARY KEY, order_id INTEGER, amount_cents INTEGER);

Business rules:
- Only orders with status = 'completed' contribute revenue.
- Net revenue = completed order amounts minus refunds that belong to completed orders.
- An order may have zero, one, or several refunds; refunds must never multiply order revenue.
- A customer with a missing (NULL or empty) region is reported as region 'Unknown'.
- All money is integer cents. Do not convert to dollars.
"""


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    title: str
    instructions: str
    expected_columns: tuple[str, ...]
    starter_sql: str
    # Competency -> points this task contributes. Sums across tasks must equal
    # COMPETENCY_WEIGHTS; grading.py splits these points over hidden tests.
    points: dict[str, int]

    @property
    def possible(self) -> int:
        return sum(self.points.values())


TASKS: tuple[TaskDefinition, ...] = (
    TaskDefinition(
        id="t1",
        title="Trace valid orders to regions",
        instructions=(
            "Return one row per completed order with its customer's region. "
            "Join orders to customers, keep only completed orders, report a "
            "missing region as 'Unknown', and sort by order_id ascending."
        ),
        expected_columns=("order_id", "region", "amount_cents"),
        starter_sql=(
            "SELECT id AS order_id, customer_id, amount_cents, status\n"
            "FROM orders\n"
            "ORDER BY id;"
        ),
        points={SQL_JOINS: 25, SQL_FILTERING: 10},
    ),
    TaskDefinition(
        id="t2",
        title="Recalculate gross revenue",
        instructions=(
            "Return gross revenue in cents per region from completed orders "
            "only, excluding pending and cancelled orders. Sort by region "
            "ascending."
        ),
        expected_columns=("region", "gross_revenue_cents"),
        starter_sql=(
            "-- Current dashboard query: counts every order status.\n"
            "SELECT c.region, SUM(o.amount_cents) AS gross_revenue_cents\n"
            "FROM orders o\n"
            "JOIN customers c ON c.id = o.customer_id\n"
            "GROUP BY c.region\n"
            "ORDER BY c.region;"
        ),
        points={SQL_FILTERING: 10, SQL_AGGREGATION: 15},
    ),
    TaskDefinition(
        id="t3",
        title="Correct net revenue after refunds",
        instructions=(
            "Return net revenue in cents per region: completed order revenue "
            "minus refunds on those orders. Handle orders with no refund, "
            "partial refunds, and multiple refunds without double-counting "
            "order amounts. Sort by region ascending."
        ),
        expected_columns=("region", "net_revenue_cents"),
        starter_sql=(
            "-- Current dashboard query: joins refunds directly.\n"
            "SELECT c.region,\n"
            "       SUM(o.amount_cents) - SUM(COALESCE(r.amount_cents, 0)) AS net_revenue_cents\n"
            "FROM orders o\n"
            "JOIN customers c ON c.id = o.customer_id\n"
            "LEFT JOIN refunds r ON r.order_id = o.id\n"
            "WHERE o.status = 'completed'\n"
            "GROUP BY c.region\n"
            "ORDER BY c.region;"
        ),
        points={SQL_AGGREGATION: 10, SQL_REFUND_EDGE_CASES: 30},
    ),
)

TASKS_BY_ID = {task.id: task for task in TASKS}


def competency_tasks(project_id: str, skill_id: str) -> dict[str, int]:
    """All designated task contributions needed to demonstrate a competency."""
    if project_id != PROJECT_ID:
        return {}
    return {task.id: task.points[skill_id] for task in TASKS if skill_id in task.points}


def get_task(project_id: str, task_id: str) -> TaskDefinition | None:
    if project_id != PROJECT_ID:
        return None
    return TASKS_BY_ID.get(task_id)


def get_public_project(project_id: str) -> ProjectResponse | None:
    """Client-safe project description, or None for an unknown project."""
    if project_id != PROJECT_ID:
        return None
    return ProjectResponse(
        id=PROJECT_ID,
        title=PROJECT_TITLE,
        scenario=SCENARIO,
        schema_text=SCHEMA_TEXT,
        tasks=[
            ProjectTask(
                id=task.id,
                title=task.title,
                instructions=task.instructions,
                expected_columns=list(task.expected_columns),
                starter_sql=task.starter_sql,
            )
            for task in TASKS
        ],
        competencies=list(COMPETENCIES),
    )


def _check_allocations() -> None:
    totals = {skill: 0 for skill in COMPETENCIES}
    for task in TASKS:
        for skill, points in task.points.items():
            totals[skill] += points
    if totals != COMPETENCY_WEIGHTS or sum(totals.values()) != 100:
        raise RuntimeError(f"Task point allocations do not match weights: {totals}")


_check_allocations()


@dataclass(frozen=True)
class ProjectTemplate:
    id: str
    title: str
    competencies: frozenset[str]


PROJECT_REGISTRY = (
    ProjectTemplate(
        id=PROJECT_ID,
        title=PROJECT_TITLE,
        competencies=frozenset(COMPETENCIES),
    ),
)
