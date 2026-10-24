import time

import pytest

from gapmap.apps.api.services.projects.executor import MAX_SQL_LENGTH, execute_query
from gapmap.apps.api.services.projects.fixtures import PUBLIC_FIXTURE


def run(sql: str, max_rows: int = 20):
    return execute_query(sql, PUBLIC_FIXTURE, max_rows=max_rows)


def assert_rejected(sql: str) -> str:
    result = run(sql)
    assert result.error, f"expected rejection for: {sql!r}"
    assert result.columns == [] and result.rows == []
    assert "Traceback" not in result.error
    return result.error


def assert_still_healthy() -> None:
    result = run("SELECT COUNT(*) AS n FROM orders")
    assert result.error is None
    assert result.rows == [[len(PUBLIC_FIXTURE.orders)]]


# --- Malicious queries -------------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE orders",
        "drop table if exists refunds;",
        "WITH x AS (SELECT 1) DELETE FROM orders",
    ],
)
def test_drop_and_writes_rejected(sql: str) -> None:
    assert_rejected(sql)
    assert_still_healthy()


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO orders VALUES (999, 1, 1, 'completed', '2026-01-01')",
        "UPDATE orders SET amount_cents = 0",
        "DELETE FROM refunds",
        "CREATE TABLE evil (x)",
        "CREATE TEMP TABLE evil AS SELECT * FROM orders",
        "ALTER TABLE orders ADD COLUMN x",
        "REPLACE INTO orders VALUES (101, 1, 1, 'completed', '2026-01-01')",
        "VACUUM",
        "BEGIN",
    ],
)
def test_other_side_effects_rejected(sql: str) -> None:
    assert_rejected(sql)
    assert_still_healthy()


@pytest.mark.parametrize(
    "sql",
    [
        "ATTACH DATABASE 'evil.db' AS evil",
        "attach 'evil.db' as evil;",
        "SELECT 1; ATTACH DATABASE 'evil.db' AS evil",
    ],
)
def test_attach_rejected_and_creates_no_file(sql: str, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert_rejected(sql)
    assert not (tmp_path / "evil.db").exists()


@pytest.mark.parametrize(
    "sql",
    [
        "PRAGMA table_info(orders)",
        "PRAGMA writable_schema = ON",
        "pragma query_only = OFF;",
        "SELECT * FROM pragma_table_info('orders')",
        "SELECT name FROM sqlite_master",
    ],
)
def test_pragma_and_schema_introspection_rejected(sql: str) -> None:
    assert_rejected(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DROP TABLE orders",
        "SELECT 1; SELECT 2",
        "SELECT * FROM orders; /* hidden */ DELETE FROM orders",
        "SELECT 1;\n-- comment\nDROP TABLE customers;",
        "SELECT ';'; DROP TABLE orders",
    ],
)
def test_multiple_statements_rejected(sql: str) -> None:
    assert_rejected(sql)
    assert_still_healthy()


def test_runaway_recursive_cte_is_interrupted() -> None:
    started = time.monotonic()
    error = assert_rejected(
        "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) "
        "SELECT COUNT(*) FROM r"
    )
    assert time.monotonic() - started < 5
    assert "limit" in error.lower()
    assert_still_healthy()


def test_cartesian_explosion_is_interrupted() -> None:
    started = time.monotonic()
    assert_rejected(
        "SELECT COUNT(*) FROM orders a, orders b, orders c, orders d, orders e, "
        "orders f, orders g, orders h, orders i, orders j, orders k, orders l"
    )
    assert time.monotonic() - started < 5


def test_unbounded_recursive_rows_are_capped_not_runaway() -> None:
    result = run(
        "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT n FROM r",
        max_rows=5,
    )
    assert result.error is None
    assert result.rows == [[1], [2], [3], [4], [5]]
    assert result.truncated is True


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT load_extension('evil')",
        "SELECT length(zeroblob(1000000000))",
        "SELECT length(replace(printf('%.*c', 900000, 'x'), 'x', 'xxxxxxxxxx'))",
    ],
)
def test_extension_loading_and_memory_bombs_rejected(sql: str) -> None:
    assert_rejected(sql)
    assert_still_healthy()


def test_oversized_printf_is_capped_without_allocating() -> None:
    started = time.monotonic()
    result = run("SELECT length(printf('%.*c', 500000000, 'x'))")
    assert time.monotonic() - started < 1
    assert result.error or result.rows == [[None]]
    assert_still_healthy()


def test_oversized_sql_rejected() -> None:
    sql = "SELECT 1" + " " * MAX_SQL_LENGTH
    error = assert_rejected(sql)
    assert "10,000" in error


@pytest.mark.parametrize("sql", ["", "   ", "-- only a comment", ";"])
def test_empty_sql_rejected(sql: str) -> None:
    assert_rejected(sql)


# --- Safe errors -------------------------------------------------------------


def test_syntax_error_is_useful_and_sanitized() -> None:
    error = assert_rejected("SELEC * FROM orders")
    assert "syntax" in error.lower()
    assert "sqlite3" not in error.lower()


def test_unknown_column_error_is_useful() -> None:
    error = assert_rejected("SELECT revenue FROM orders")
    assert "revenue" in error


def test_rejection_message_does_not_echo_query() -> None:
    error = assert_rejected("DROP TABLE orders -- secret-marker")
    assert "secret-marker" not in error


# --- Allowed queries ---------------------------------------------------------


def test_simple_select_returns_columns_and_rows() -> None:
    result = run("SELECT id, status FROM orders WHERE id = 101")
    assert result.error is None
    assert result.columns == ["id", "status"]
    assert result.rows == [[101, "completed"]]
    assert result.truncated is False


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1;",
        "SELECT 1; -- trailing comment",
        "  -- leading comment\nSELECT 1",
        "/* block */ SELECT 1 /* ; */",
        "WITH t AS (SELECT 1 AS x) SELECT x FROM t",
        "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 3) "
        "SELECT SUM(n) FROM r",
        "SELECT x FROM (SELECT 1 AS x)",
        "SELECT CASE WHEN region IS NULL OR region = '' THEN 'Unknown' ELSE region END "
        "FROM customers",
        "SELECT COALESCE(SUM(amount_cents), 0), ROW_NUMBER() OVER (ORDER BY 1) FROM refunds",
    ],
)
def test_read_only_variants_allowed(sql: str) -> None:
    result = run(sql)
    assert result.error is None, result.error


def test_rows_are_truncated_to_max_rows() -> None:
    result = run("SELECT id FROM orders ORDER BY id", max_rows=2)
    assert result.rows == [[101], [102]]
    assert result.truncated is True


def test_each_execution_uses_a_fresh_database() -> None:
    first = run("SELECT COUNT(*) FROM orders")
    second = run("SELECT COUNT(*) FROM orders")
    assert first.rows == second.rows == [[len(PUBLIC_FIXTURE.orders)]]


def test_blob_and_non_finite_values_are_json_safe() -> None:
    result = run("SELECT x'00ff', 1e999")
    assert result.error is None
    blob, infinity = result.rows[0]
    assert isinstance(blob, str) and isinstance(infinity, str)
