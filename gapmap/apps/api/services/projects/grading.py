"""Deterministic grading against hidden fixtures.

Expected outputs come from a plain-Python oracle over fixture rows, written
independently of any SQL. Each hidden test declares its task, competency,
fixture, points, and expected output; a test passes only when the candidate's
query output (not its text) matches. Nothing here calls an LLM.

Client feedback is limited to a public label and a generic diagnostic. Hidden
rows, expected values, and row counts are never included.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from gapmap.apps.api.contracts import (
    CompetencyScore,
    EvidenceStatus,
    PublicTestFeedback,
    ResultCell,
    TaskScore,
)
from gapmap.apps.api.services.projects.executor import QueryResult, execute_query
from gapmap.apps.api.services.projects.fixtures import HIDDEN_FIXTURES, Fixture
from gapmap.apps.api.services.projects.registry import (
    SQL_AGGREGATION,
    SQL_FILTERING,
    SQL_JOINS,
    SQL_REFUND_EDGE_CASES,
    TASKS,
    UNKNOWN_REGION,
    TaskDefinition,
)


MAX_GRADING_ROWS = 1_000

Row = tuple[ResultCell, ...]


# --- Oracle ------------------------------------------------------------------


def _region_of(fixture: Fixture) -> dict[int, str]:
    return {
        customer_id: region if region else UNKNOWN_REGION
        for customer_id, _, region in fixture.customers
    }


def _completed_orders(fixture: Fixture):
    return [order for order in fixture.orders if order[3] == "completed"]


def oracle_t1(fixture: Fixture) -> list[Row]:
    regions = _region_of(fixture)
    return sorted(
        (order_id, regions[customer_id], amount)
        for order_id, customer_id, amount, _, _ in _completed_orders(fixture)
    )


def oracle_t2(fixture: Fixture) -> list[Row]:
    regions = _region_of(fixture)
    gross: dict[str, int] = defaultdict(int)
    for _, customer_id, amount, _, _ in _completed_orders(fixture):
        gross[regions[customer_id]] += amount
    return sorted(gross.items())


def oracle_t3(fixture: Fixture) -> list[Row]:
    regions = _region_of(fixture)
    refunded: dict[int, int] = defaultdict(int)
    for _, order_id, amount in fixture.refunds:
        refunded[order_id] += amount
    net: dict[str, int] = defaultdict(int)
    for order_id, customer_id, amount, _, _ in _completed_orders(fixture):
        net[regions[customer_id]] += amount - refunded[order_id]
    return sorted(net.items())


ORACLES = {"t1": oracle_t1, "t2": oracle_t2, "t3": oracle_t3}


# --- Hidden test configuration ----------------------------------------------


@dataclass(frozen=True)
class HiddenTest:
    id: str
    task_id: str
    competency: str
    points: int
    fixture: str
    label: str
    hint: str
    expected: tuple[Row, ...] = field(init=False)

    def __post_init__(self) -> None:
        rows = ORACLES[self.task_id](HIDDEN_FIXTURES[self.fixture])
        object.__setattr__(self, "expected", tuple(rows))


HIDDEN_TESTS: tuple[HiddenTest, ...] = (
    # T1: joins 25, filtering 10.
    HiddenTest(
        "t1-join-basic", "t1", SQL_JOINS, 9, "multiple_refunds",
        "Each completed order is matched to its customer's region",
        "Join orders to customers on the customer ID.",
    ),
    HiddenTest(
        "t1-join-shared-region", "t1", SQL_JOINS, 8, "partial_refunds",
        "Orders from several customers in the same region",
        "Every completed order should appear once with its own region.",
    ),
    HiddenTest(
        "t1-join-missing-region", "t1", SQL_JOINS, 8, "missing_region",
        "Customers with a missing region are reported as 'Unknown'",
        "Treat NULL and empty regions as 'Unknown'.",
    ),
    HiddenTest(
        "t1-filter-status", "t1", SQL_FILTERING, 10, "cancelled_orders",
        "Only completed orders are listed",
        "Exclude pending and cancelled orders.",
    ),
    # T2: filtering 10, aggregation 15.
    HiddenTest(
        "t2-filter-status", "t2", SQL_FILTERING, 5, "cancelled_orders",
        "Gross revenue excludes cancelled and pending orders",
        "Only completed orders contribute revenue.",
    ),
    HiddenTest(
        "t2-filter-mixed", "t2", SQL_FILTERING, 5, "multi_customer_region",
        "Mixed statuses across several regions",
        "Only completed orders contribute revenue.",
    ),
    HiddenTest(
        "t2-agg-by-region", "t2", SQL_AGGREGATION, 5, "partial_refunds",
        "Revenue is summed per region, not per customer",
        "Group by region and sum order amounts.",
    ),
    HiddenTest(
        "t2-agg-no-refund-join", "t2", SQL_AGGREGATION, 5, "multiple_refunds",
        "Gross revenue is not inflated by related rows",
        "Each order amount should be counted exactly once.",
    ),
    HiddenTest(
        "t2-agg-missing-region", "t2", SQL_AGGREGATION, 5, "missing_region",
        "Orders with a missing region are grouped under 'Unknown'",
        "Treat NULL and empty regions as 'Unknown' before grouping.",
    ),
    # T3: aggregation 10, refund edge cases 30.
    HiddenTest(
        "t3-agg-baseline", "t3", SQL_AGGREGATION, 5, "baseline",
        "Net revenue per region on a typical dataset",
        "Group completed orders by region and subtract their refunds.",
    ),
    HiddenTest(
        "t3-agg-shared-region", "t3", SQL_AGGREGATION, 5, "multi_customer_region",
        "Regions with several customers and mixed statuses",
        "Aggregate per region across all of its customers.",
    ),
    HiddenTest(
        "t3-refund-none", "t3", SQL_REFUND_EDGE_CASES, 6, "no_refunds",
        "Orders with no refunds keep their full amount",
        "A missing refund counts as zero; do not drop unrefunded orders.",
    ),
    HiddenTest(
        "t3-refund-partial", "t3", SQL_REFUND_EDGE_CASES, 6, "partial_refunds",
        "Partial and full refunds are subtracted",
        "Subtract each order's refunds; a fully refunded region nets to zero.",
    ),
    HiddenTest(
        "t3-refund-multiple", "t3", SQL_REFUND_EDGE_CASES, 8, "multiple_refunds",
        "Orders with several refunds are not double-counted",
        "Joining refunds directly repeats the order amount once per refund. "
        "Total refunds per order before combining with orders.",
    ),
    HiddenTest(
        "t3-refund-excluded-status", "t3", SQL_REFUND_EDGE_CASES, 5, "cancelled_orders",
        "Refunds on cancelled or pending orders are ignored",
        "Only refunds belonging to completed orders reduce revenue.",
    ),
    HiddenTest(
        "t3-refund-missing-region", "t3", SQL_REFUND_EDGE_CASES, 5, "missing_region",
        "Refunds for customers with a missing region land in 'Unknown'",
        "Treat NULL and empty regions as 'Unknown'.",
    ),
)


def tests_for_task(task_id: str) -> list[HiddenTest]:
    return [test for test in HIDDEN_TESTS if test.task_id == task_id]


def _check_configuration() -> None:
    for task in TASKS:
        totals: dict[str, int] = defaultdict(int)
        for test in tests_for_task(task.id):
            totals[test.competency] += test.points
        if dict(totals) != task.points:
            raise RuntimeError(f"Hidden tests for {task.id} do not match points: {dict(totals)}")


_check_configuration()


# --- Comparison --------------------------------------------------------------


def normalize_value(value: ResultCell) -> ResultCell:
    """Integral floats become ints so SUM/CAST variants compare as cents."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


@dataclass(frozen=True)
class Comparison:
    passed: bool
    explanation: str


def compare_output(
    result: QueryResult, expected_columns: tuple[str, ...], expected: tuple[Row, ...]
) -> Comparison:
    if result.error:
        return Comparison(False, result.error)

    names = [column.strip().lower() for column in result.columns]
    if sorted(names) != sorted(expected_columns):
        return Comparison(
            False,
            f"Expected columns {', '.join(expected_columns)}; "
            f"got {', '.join(result.columns) or 'none'}.",
        )
    if result.truncated:
        return Comparison(False, "The query returned far more rows than expected.")

    positions = [names.index(column) for column in expected_columns]
    actual = [
        tuple(normalize_value(row[position]) for position in positions) for row in result.rows
    ]
    wanted = list(expected)

    if len(actual) > len(wanted):
        return Comparison(False, "The query returned too many rows.")
    if len(actual) < len(wanted):
        return Comparison(False, "The query returned too few rows.")
    if actual == wanted:
        return Comparison(True, "Passed.")
    if sorted(actual, key=repr) == sorted(wanted, key=repr):
        return Comparison(False, "Rows are correct but not in the required order.")
    return Comparison(False, "One or more values differ from the expected result.")


# --- Grading -----------------------------------------------------------------


@dataclass(frozen=True)
class GradeResult:
    task_score: TaskScore
    competency_scores: list[CompetencyScore]
    public_test_feedback: list[PublicTestFeedback]


def competency_status(passed: int, total: int) -> EvidenceStatus:
    if total and passed == total:
        return EvidenceStatus.DEMONSTRATED_ON_PROJECT
    if passed:
        return EvidenceStatus.PARTIALLY_DEMONSTRATED
    return EvidenceStatus.UNVERIFIED


def grade_task(task: TaskDefinition, sql: str) -> GradeResult:
    """Run ``sql`` on each hidden fixture for ``task`` and score the outputs."""
    tests = tests_for_task(task.id)
    results: dict[str, QueryResult] = {}
    feedback: list[PublicTestFeedback] = []
    earned: dict[str, int] = defaultdict(int)
    possible: dict[str, int] = defaultdict(int)
    passed_count: dict[str, int] = defaultdict(int)
    test_count: dict[str, int] = defaultdict(int)

    for test in tests:
        if test.fixture not in results:
            results[test.fixture] = execute_query(
                sql, HIDDEN_FIXTURES[test.fixture], max_rows=MAX_GRADING_ROWS
            )
        comparison = compare_output(results[test.fixture], task.expected_columns, test.expected)

        possible[test.competency] += test.points
        test_count[test.competency] += 1
        if comparison.passed:
            earned[test.competency] += test.points
            passed_count[test.competency] += 1
            explanation = comparison.explanation
        else:
            explanation = f"{comparison.explanation} Hint: {test.hint}"
        feedback.append(
            PublicTestFeedback(label=test.label, passed=comparison.passed, explanation=explanation)
        )

    competency_scores = [
        CompetencyScore(
            skill_id=skill,
            earned=earned[skill],
            possible=possible[skill],
            status=competency_status(passed_count[skill], test_count[skill]),
        )
        for skill in task.points
    ]
    return GradeResult(
        task_score=TaskScore(earned=sum(earned.values()), possible=sum(possible.values())),
        competency_scores=competency_scores,
        public_test_feedback=feedback,
    )
