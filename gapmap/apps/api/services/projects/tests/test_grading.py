import json
import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from gapmap.apps.api.contracts import EvidenceStatus
from gapmap.apps.api.main import create_app
from gapmap.apps.api.services.demo_analysis import DemoAnalysisService
from gapmap.apps.api.services.projects.executor import execute_query
from gapmap.apps.api.services.projects.fixtures import HIDDEN_FIXTURES, PUBLIC_FIXTURE
from gapmap.apps.api.services.projects.grading import (
    HIDDEN_TESTS,
    ORACLES,
    competency_status,
    grade_task,
)
from gapmap.apps.api.services.projects.grading import tests_for_task as hidden_tests_for
from gapmap.apps.api.services.projects.registry import (
    COMPETENCY_WEIGHTS,
    PROJECT_ID,
    SQL_REFUND_EDGE_CASES,
    TASKS,
    TASKS_BY_ID,
)
from gapmap.apps.api.services.projects.routes import SqlProjectService


# Reference solutions live only in tests; the grader never sees them.
REGION = "CASE WHEN c.region IS NULL OR c.region = '' THEN 'Unknown' ELSE c.region END"
REFERENCE = {
    "t1": f"""
        SELECT o.id AS order_id, {REGION} AS region, o.amount_cents
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE o.status = 'completed'
        ORDER BY o.id""",
    "t2": f"""
        SELECT {REGION} AS region, SUM(o.amount_cents) AS gross_revenue_cents
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE o.status = 'completed'
        GROUP BY 1 ORDER BY 1""",
    "t3": f"""
        WITH order_refunds AS (
          SELECT order_id, SUM(amount_cents) AS refunded FROM refunds GROUP BY order_id
        )
        SELECT {REGION} AS region,
               SUM(o.amount_cents - COALESCE(r.refunded, 0)) AS net_revenue_cents
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        LEFT JOIN order_refunds r ON r.order_id = o.id
        WHERE o.status = 'completed'
        GROUP BY 1 ORDER BY 1""",
}

ALTERNATIVES = {
    "t1": [
        # LEFT JOIN, NULLIF/COALESCE, reordered and upper-cased columns.
        """SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS REGION,
                  o.amount_cents, o.id AS order_id
           FROM orders o LEFT JOIN customers c ON o.customer_id = c.id
           WHERE o.status IN ('completed')
           ORDER BY order_id;""",
        # Correlated subquery instead of a join.
        """SELECT id AS order_id,
                  (SELECT COALESCE(NULLIF(region, ''), 'Unknown')
                   FROM customers WHERE customers.id = orders.customer_id) AS region,
                  amount_cents
           FROM orders WHERE status = 'completed' ORDER BY 1""",
    ],
    "t2": [
        # Pre-filtered CTE, float arithmetic that stays integral.
        """WITH done AS (SELECT * FROM orders WHERE status = 'completed')
           SELECT IFNULL(NULLIF(c.region, ''), 'Unknown') AS region,
                  SUM(d.amount_cents * 1.0) AS gross_revenue_cents
           FROM done d JOIN customers c ON c.id = d.customer_id
           GROUP BY 1 ORDER BY 1""",
        # Conditional aggregation with HAVING.
        """SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
                  SUM(CASE WHEN o.status = 'completed' THEN o.amount_cents ELSE 0 END)
                    AS gross_revenue_cents
           FROM orders o JOIN customers c ON c.id = o.customer_id
           GROUP BY 1
           HAVING SUM(o.status = 'completed') > 0
           ORDER BY 1""",
    ],
    "t3": [
        # Gross minus refunds computed in two separate aggregates.
        """WITH base AS (
             SELECT o.id, o.amount_cents,
                    COALESCE(NULLIF(c.region, ''), 'Unknown') AS region
             FROM orders o JOIN customers c ON c.id = o.customer_id
             WHERE o.status = 'completed'
           ),
           gross AS (SELECT region, SUM(amount_cents) AS g FROM base GROUP BY region),
           refunded AS (
             SELECT b.region, SUM(r.amount_cents) AS rf
             FROM refunds r JOIN base b ON b.id = r.order_id GROUP BY b.region
           )
           SELECT gross.region, g - COALESCE(rf, 0) AS net_revenue_cents
           FROM gross LEFT JOIN refunded ON refunded.region = gross.region
           ORDER BY gross.region""",
        # Correlated per-order refund subquery.
        """SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
                  SUM(o.amount_cents
                      - (SELECT COALESCE(SUM(r.amount_cents), 0)
                         FROM refunds r WHERE r.order_id = o.id)) AS net_revenue_cents
           FROM orders o JOIN customers c ON c.id = o.customer_id
           WHERE o.status = 'completed'
           GROUP BY 1 ORDER BY 1""",
    ],
}

NAIVE_REFUND_JOIN = TASKS_BY_ID["t3"].starter_sql
IGNORES_REFUNDS = REFERENCE["t2"].replace("gross_revenue_cents", "net_revenue_cents")


def grade(task_id: str, sql: str):
    return grade_task(TASKS_BY_ID[task_id], sql)


def failed_test_ids(task_id: str, sql: str) -> set[str]:
    result = grade(task_id, sql)
    labels = {test.label: test.id for test in hidden_tests_for(task_id)}
    return {labels[item.label] for item in result.public_test_feedback if not item.passed}


# --- Configuration -----------------------------------------------------------


def test_points_sum_to_fixed_weights() -> None:
    totals = {skill: 0 for skill in COMPETENCY_WEIGHTS}
    for test in HIDDEN_TESTS:
        totals[test.competency] += test.points
    assert totals == COMPETENCY_WEIGHTS
    assert sum(test.points for test in HIDDEN_TESTS) == 100


def test_required_edge_cases_each_have_a_refund_test() -> None:
    refund_fixtures = {
        test.fixture for test in HIDDEN_TESTS if test.competency == SQL_REFUND_EDGE_CASES
    }
    assert {"no_refunds", "multiple_refunds", "cancelled_orders", "missing_region"} <= refund_fixtures
    assert HIDDEN_FIXTURES["no_refunds"].refunds == ()
    assert any(
        sum(1 for refund in HIDDEN_FIXTURES["multiple_refunds"].refunds if refund[1] == order[0]) > 1
        for order in HIDDEN_FIXTURES["multiple_refunds"].orders
    )


def test_test_labels_are_unique_within_a_task() -> None:
    for task in TASKS:
        labels = [test.label for test in hidden_tests_for(task.id)]
        assert len(labels) == len(set(labels))


@pytest.mark.parametrize("task_id", ["t1", "t2", "t3"])
@pytest.mark.parametrize("fixture_name", sorted(HIDDEN_FIXTURES))
def test_oracle_agrees_with_reference_sql(task_id: str, fixture_name: str) -> None:
    result = execute_query(REFERENCE[task_id], HIDDEN_FIXTURES[fixture_name], max_rows=1000)
    assert result.error is None
    assert [tuple(row) for row in result.rows] == ORACLES[task_id](HIDDEN_FIXTURES[fixture_name])


# --- Acceptance: reference scores 100 ---------------------------------------


def test_reference_scores_exactly_100_on_all_hidden_cases() -> None:
    total = 0
    for task in TASKS:
        result = grade(task.id, REFERENCE[task.id])
        assert all(item.passed for item in result.public_test_feedback)
        assert result.task_score.earned == result.task_score.possible == task.possible
        assert {score.status for score in result.competency_scores} == {
            EvidenceStatus.DEMONSTRATED_ON_PROJECT
        }
        total += result.task_score.earned
    assert total == 100


# --- Acceptance: refund-ignoring and naive-join queries fail ----------------


def test_query_ignoring_refunds_fails_refund_tests() -> None:
    result = grade("t3", IGNORES_REFUNDS)
    refund = next(s for s in result.competency_scores if s.skill_id == SQL_REFUND_EDGE_CASES)
    assert refund.earned < refund.possible
    assert refund.status is not EvidenceStatus.DEMONSTRATED_ON_PROJECT
    assert result.task_score.earned < result.task_score.possible
    assert {"t3-refund-partial", "t3-refund-multiple"} <= failed_test_ids("t3", IGNORES_REFUNDS)


def test_query_ignoring_refunds_cannot_reach_100_overall() -> None:
    total = (
        grade("t1", REFERENCE["t1"]).task_score.earned
        + grade("t2", REFERENCE["t2"]).task_score.earned
        + grade("t3", IGNORES_REFUNDS).task_score.earned
    )
    assert total < 100


def test_naive_refund_join_fails_multi_refund_fixture() -> None:
    failed = failed_test_ids("t3", NAIVE_REFUND_JOIN)
    assert "t3-refund-multiple" in failed
    feedback = {item.label: item for item in grade("t3", NAIVE_REFUND_JOIN).public_test_feedback}
    multi = next(t for t in HIDDEN_TESTS if t.id == "t3-refund-multiple")
    assert "double" in multi.label.lower()
    assert "once per refund" in feedback[multi.label].explanation


def test_naive_refund_join_in_gross_revenue_is_caught() -> None:
    sql = """SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
                    SUM(o.amount_cents) AS gross_revenue_cents
             FROM orders o JOIN customers c ON c.id = o.customer_id
             LEFT JOIN refunds r ON r.order_id = o.id
             WHERE o.status = 'completed'
             GROUP BY 1 ORDER BY 1"""
    assert "t2-agg-no-refund-join" in failed_test_ids("t2", sql)


def test_inner_join_to_refunds_fails_empty_refunds_fixture() -> None:
    sql = REFERENCE["t3"].replace("LEFT JOIN order_refunds", "JOIN order_refunds")
    assert "t3-refund-none" in failed_test_ids("t3", sql)


def test_refunds_on_cancelled_orders_must_not_count() -> None:
    sql = f"""
        SELECT {REGION} AS region,
               (SELECT SUM(o2.amount_cents) FROM orders o2 JOIN customers c2
                  ON c2.id = o2.customer_id WHERE o2.status = 'completed'
                  AND COALESCE(NULLIF(c2.region, ''), 'Unknown') = {REGION})
             - COALESCE((SELECT SUM(r.amount_cents) FROM refunds r
                  JOIN orders o3 ON o3.id = r.order_id JOIN customers c3
                  ON c3.id = o3.customer_id
                  WHERE COALESCE(NULLIF(c3.region, ''), 'Unknown') = {REGION}), 0)
               AS net_revenue_cents
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE o.status = 'completed'
        GROUP BY 1 ORDER BY 1"""
    refund_failures = {t for t in failed_test_ids("t3", sql) if t.startswith("t3-refund")}
    assert refund_failures == {"t3-refund-excluded-status"}


@pytest.mark.parametrize(
    ("task_id", "sql", "test_id"),
    [
        ("t1", REFERENCE["t1"].replace("WHERE o.status = 'completed'", ""), "t1-filter-status"),
        (
            "t2",
            REFERENCE["t2"].replace("o.status = 'completed'", "o.status != 'cancelled'"),
            "t2-filter-status",
        ),
        ("t1", REFERENCE["t1"].replace(REGION, "COALESCE(c.region, 'Unknown')"), "t1-join-missing-region"),
        ("t2", REFERENCE["t2"].replace(REGION, "c.region"), "t2-agg-missing-region"),
    ],
)
def test_specific_mistakes_fail_their_designated_test(task_id: str, sql: str, test_id: str) -> None:
    assert test_id in failed_test_ids(task_id, sql)


# --- Acceptance: logically correct alternatives accepted ---------------------


@pytest.mark.parametrize(
    ("task_id", "sql"),
    [(task_id, sql) for task_id, options in ALTERNATIVES.items() for sql in options],
)
def test_alternative_correct_solutions_score_full_marks(task_id: str, sql: str) -> None:
    result = grade(task_id, sql)
    failures = [item for item in result.public_test_feedback if not item.passed]
    assert not failures, failures
    assert result.task_score.earned == TASKS_BY_ID[task_id].possible


# --- Comparison rules --------------------------------------------------------


def test_wrong_order_fails_with_order_diagnostic() -> None:
    sql = REFERENCE["t2"].replace("ORDER BY 1", "ORDER BY 1 DESC")
    result = grade("t2", sql)
    assert any("order" in item.explanation and not item.passed for item in result.public_test_feedback)
    assert result.task_score.earned < result.task_score.possible


def test_dollar_conversion_is_rejected() -> None:
    sql = REFERENCE["t2"].replace("SUM(o.amount_cents)", "SUM(o.amount_cents) / 100.0")
    assert grade("t2", sql).task_score.earned == 0


def test_wrong_column_names_fail_with_column_diagnostic() -> None:
    sql = REFERENCE["t2"].replace("AS gross_revenue_cents", "AS revenue")
    result = grade("t2", sql)
    assert result.task_score.earned == 0
    assert all("Expected columns" in item.explanation for item in result.public_test_feedback)


def test_row_count_feedback_does_not_reveal_direction() -> None:
    extra = REFERENCE["t1"].replace("WHERE o.status = 'completed'", "")
    missing = REFERENCE["t1"].replace("ORDER BY o.id", "ORDER BY o.id LIMIT 1")
    filter_test = next(t for t in HIDDEN_TESTS if t.id == "t1-filter-status")
    explanations = []
    for sql in (extra, missing):
        feedback = {item.label: item for item in grade("t1", sql).public_test_feedback}
        explanations.append(feedback[filter_test.label].explanation)
    assert explanations[0] == explanations[1]
    assert "wrong number of rows" in explanations[0]
    for word in ("many", "few", "more", "fewer", "less"):
        assert word not in explanations[0].lower()


def test_competency_status_rules() -> None:
    assert competency_status(3, 3) is EvidenceStatus.DEMONSTRATED_ON_PROJECT
    assert competency_status(1, 3) is EvidenceStatus.PARTIALLY_DEMONSTRATED
    assert competency_status(0, 3) is EvidenceStatus.UNVERIFIED


def test_partial_pass_is_partially_demonstrated() -> None:
    result = grade("t3", NAIVE_REFUND_JOIN)
    refund = next(s for s in result.competency_scores if s.skill_id == SQL_REFUND_EDGE_CASES)
    assert 0 < refund.earned < refund.possible
    assert refund.status is EvidenceStatus.PARTIALLY_DEMONSTRATED


def test_grading_is_deterministic() -> None:
    assert grade("t3", NAIVE_REFUND_JOIN) == grade("t3", NAIVE_REFUND_JOIN)


# --- API: safe execution and errors -----------------------------------------


@pytest.fixture
def client() -> TestClient:
    # Pin the deterministic demo analysis so these tests do not depend on
    # OPENAI_API_KEY or GAPMAP_DEMO_MODE being set.
    app = create_app(analysis_service=DemoAnalysisService(), project_service=SqlProjectService())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session_id(client: TestClient) -> str:
    fixture = client.get("/api/demo/fixture").json()
    return client.post("/api/analyze", json=fixture).json()["session_id"]


def post(client: TestClient, action: str, session_id: str, task_id: str, sql: str):
    return client.post(
        f"/api/projects/{PROJECT_ID}/{action}",
        json={"session_id": session_id, "task_id": task_id, "sql": sql},
    )


MALICIOUS = [
    "DROP TABLE orders",
    "SELECT 1; DROP TABLE orders",
    "ATTACH DATABASE 'evil.db' AS evil",
    "PRAGMA table_info(orders)",
    "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT COUNT(*) FROM r",
]


@pytest.mark.parametrize("sql", MALICIOUS)
def test_malicious_run_rejected_safely(client: TestClient, session_id: str, sql: str) -> None:
    response = post(client, "run", session_id, "t1", sql)
    assert response.status_code == 200
    body = response.json()
    assert body["error"] and body["rows"] == []
    assert client.get("/api/health").json() == {"status": "ok"}
    healthy = post(client, "run", session_id, "t1", "SELECT COUNT(*) FROM orders").json()
    assert healthy["rows"] == [[len(PUBLIC_FIXTURE.orders)]]


@pytest.mark.parametrize("sql", MALICIOUS)
def test_malicious_submit_scores_zero(client: TestClient, session_id: str, sql: str) -> None:
    response = post(client, "submit", session_id, "t3", sql)
    assert response.status_code == 200
    body = response.json()
    assert body["task_score"]["earned"] == 0
    assert not any(item["passed"] for item in body["public_test_feedback"])


def test_oversized_sql_is_a_validation_error(client: TestClient, session_id: str) -> None:
    response = post(client, "run", session_id, "t1", "SELECT 1 " + "x" * 10_001)
    assert response.status_code == 422


def test_sql_error_feedback_is_useful_and_service_stays_healthy(
    client: TestClient, session_id: str
) -> None:
    run = post(client, "run", session_id, "t3", "SELECT net_revenue FROM orders").json()
    assert "no such column: net_revenue" in run["error"]
    submit = post(client, "submit", session_id, "t3", "SELECT net_revenue FROM orders").json()
    assert all("no such column" in item["explanation"] for item in submit["public_test_feedback"])
    for text in (run["error"], json.dumps(submit)):
        assert "Traceback" not in text and "sqlite3." not in text and ".py" not in text
    assert post(client, "submit", session_id, "t3", REFERENCE["t3"]).json()["task_score"] == {
        "earned": 40,
        "possible": 40,
    }


def test_preview_is_capped_at_20_rows(client: TestClient, session_id: str) -> None:
    sql = "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT n FROM r"
    body = post(client, "run", session_id, "t1", sql).json()
    assert len(body["rows"]) == 20 and body["truncated"] is True


def test_unknown_project_and_task_return_404(client: TestClient, session_id: str) -> None:
    assert client.get("/api/projects/missing").status_code == 404
    response = client.post(
        "/api/projects/missing/run",
        json={"session_id": session_id, "task_id": "t1", "sql": "SELECT 1"},
    )
    assert response.status_code == 404
    assert post(client, "submit", session_id, "t9", "SELECT 1").status_code == 404


def test_unknown_session_returns_404(client: TestClient) -> None:
    assert post(client, "submit", str(uuid4()), "t1", REFERENCE["t1"]).status_code == 404


# --- API: hidden data never leaks -------------------------------------------


def _hidden_markers() -> set[str]:
    public = {str(value) for row in PUBLIC_FIXTURE.customers for value in row}
    markers: set[str] = set()
    for fixture in HIDDEN_FIXTURES.values():
        markers |= {name for _, name, _ in fixture.customers}
        markers |= {region for _, _, region in fixture.customers if region}
    for test in HIDDEN_TESTS:
        markers |= {str(cell) for row in test.expected for cell in row if isinstance(cell, int) and cell >= 100}
        markers.add(test.fixture)
    return markers - public - {"Unknown"}


def _leaks(text: str) -> list[str]:
    return [marker for marker in _hidden_markers() if re.search(rf"\b{re.escape(marker)}\b", text)]


def test_project_response_has_no_grader_secrets(client: TestClient) -> None:
    body = client.get(f"/api/projects/{PROJECT_ID}").json()
    assert [task["id"] for task in body["tasks"]] == ["t1", "t2", "t3"]
    assert _leaks(json.dumps(body)) == []


@pytest.mark.parametrize("task_id", ["t1", "t2", "t3"])
def test_submit_feedback_has_no_hidden_rows_or_expected_values(
    client: TestClient, session_id: str, task_id: str
) -> None:
    for sql in (REFERENCE[task_id], TASKS_BY_ID[task_id].starter_sql, "SELECT * FROM orders"):
        body = post(client, "submit", session_id, task_id, sql).json()
        assert _leaks(json.dumps(body)) == []
        assert REFERENCE[task_id].strip()[:30] not in json.dumps(body)


# --- API: session evidence updates (Part 4 contract) ------------------------


def readiness(client: TestClient, session_id: str) -> dict:
    return client.get("/api/readiness", params={"session_id": session_id}).json()


def test_demo_flow_failing_then_passing_t3_updates_evidence(
    client: TestClient, session_id: str
) -> None:
    before = readiness(client, session_id)
    assert before["project_total"] == {"earned": 0, "possible": 0}

    wrong = post(client, "submit", session_id, "t3", NAIVE_REFUND_JOIN).json()
    assert wrong["task_score"]["earned"] < 40
    assert any(not item["passed"] for item in wrong["public_test_feedback"])
    after_wrong = readiness(client, session_id)
    refund = {e["skill_id"]: e for e in after_wrong["competency_evidence"]}[SQL_REFUND_EDGE_CASES]
    assert refund["status"] == "partially_demonstrated"

    right = post(client, "submit", session_id, "t3", REFERENCE["t3"]).json()
    assert right["task_score"] == {"earned": 40, "possible": 40}
    assert right["submission_id"] != wrong["submission_id"]
    after_right = readiness(client, session_id)
    refund = {e["skill_id"]: e for e in after_right["competency_evidence"]}[SQL_REFUND_EDGE_CASES]
    assert refund == {
        "skill_id": SQL_REFUND_EDGE_CASES,
        "status": "demonstrated_on_project",
        "earned": 30,
        "possible": 30,
        "source_project_id": PROJECT_ID,
    }
    # Latest attempt supersedes; scores are not additive.
    assert after_right["project_total"] == {"earned": 40, "possible": 40}


def test_all_tasks_demonstrate_sql_and_advance_roadmap(client: TestClient, session_id: str) -> None:
    for task in TASKS:
        post(client, "submit", session_id, task.id, REFERENCE[task.id])
    state = readiness(client, session_id)
    assert state["project_total"] == {"earned": 100, "possible": 100}
    requirements = {item["id"]: item for item in state["requirements"]}
    assert requirements["req-sql"]["evidence_status"] == "demonstrated_on_project"
    for other in ("req-react", "req-docker"):
        assert requirements[other]["evidence_status"] == "unverified"
        assert requirements[other]["verification_capability"] == "not_assessable"
    assert state["roadmap"][0]["requirement_id"] != "req-sql"
    assert "req-sql" not in {item["requirement_id"] for item in state["roadmap"]}


def test_unsubmitted_tasks_cannot_fully_demonstrate_a_competency(
    client: TestClient, session_id: str
) -> None:
    post(client, "submit", session_id, "t1", REFERENCE["t1"])
    first = readiness(client, session_id)
    filtering = next(e for e in first["competency_evidence"] if e["skill_id"] == "sql_filtering")
    assert (filtering["earned"], filtering["possible"], filtering["status"]) == (
        10, 20, "partially_demonstrated"
    )

    post(client, "submit", session_id, "t2", REFERENCE["t2"])
    second = readiness(client, session_id)
    aggregation = next(e for e in second["competency_evidence"] if e["skill_id"] == "sql_aggregation")
    assert (aggregation["earned"], aggregation["possible"], aggregation["status"]) == (
        15, 25, "partially_demonstrated"
    )
    assert next(r for r in second["requirements"] if r["id"] == "req-sql")["evidence_status"] == "partially_demonstrated"
    assert "req-sql" in {item["requirement_id"] for item in second["roadmap"]}

    post(client, "submit", session_id, "t3", REFERENCE["t3"])
    final = readiness(client, session_id)
    assert next(r for r in final["requirements"] if r["id"] == "req-sql")["evidence_status"] == "demonstrated_on_project"


def test_run_does_not_change_session_evidence(client: TestClient, session_id: str) -> None:
    post(client, "run", session_id, "t3", REFERENCE["t3"])
    assert readiness(client, session_id)["project_total"] == {"earned": 0, "possible": 0}
