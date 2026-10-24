"""Safe, read-only execution of one candidate SELECT against a fixture.

Every call builds a fresh in-memory SQLite database, seeds it, then locks it
down before the candidate SQL is prepared. Defenses are layered:

1. Lexical checks: size limit, leading keyword must be SELECT or WITH.
2. SQLite's own parser rejects trailing statements (sqlite3 refuses to prepare
   more than one statement per execute call).
3. An authorizer allowlist: only SELECT, recursive CTEs, reads of the three
   fixture tables, and an explicit set of pure functions. Everything else,
   including PRAGMA, ATTACH, writes, DDL and load_extension, is denied.
4. Runtime limits: a progress handler enforcing a VM-step and wall-clock
   budget, a string/blob length limit, and a fixed row cap.

Errors are mapped to short fixed messages; raw driver errors are only passed
through for ordinary SQL mistakes (syntax, unknown column) so feedback stays
useful without exposing internals.
"""

import math
import sqlite3
import time
from dataclasses import dataclass, field

from gapmap.apps.api.contracts import ResultCell
from gapmap.apps.api.services.projects.fixtures import Fixture, seed_database


MAX_SQL_LENGTH = 10_000
MAX_VM_STEPS = 5_000_000
MAX_SECONDS = 2.0
MAX_VALUE_LENGTH = 1_000_000
_PROGRESS_INTERVAL = 1_000

ALLOWED_TABLES = frozenset({"customers", "orders", "refunds"})
ALLOWED_FUNCTIONS = frozenset(
    {
        # Aggregates.
        "avg", "count", "group_concat", "max", "min", "string_agg", "sum", "total",
        # Window functions.
        "cume_dist", "dense_rank", "first_value", "lag", "last_value", "lead",
        "nth_value", "ntile", "percent_rank", "rank", "row_number",
        # Scalars.
        "abs", "char", "coalesce", "concat", "concat_ws", "format", "glob", "hex",
        "ifnull", "iif", "instr", "length", "like", "likelihood", "likely", "lower",
        "ltrim", "max", "min", "nullif", "octet_length", "printf", "quote", "replace",
        "round", "rtrim", "sign", "substr", "substring", "trim", "typeof", "unicode",
        "unlikely", "upper",
        # Math.
        "ceil", "ceiling", "exp", "floor", "ln", "log", "log10", "log2", "mod", "pi",
        "pow", "power", "sqrt", "trunc",
        # Dates.
        "date", "datetime", "julianday", "strftime", "time", "timediff", "unixepoch",
    }
)
# Deliberately excluded: random/randomblob (nondeterministic), zeroblob (memory),
# load_extension, and anything that reads or changes connection state.
_ALLOWED_ACTIONS = frozenset({sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE})
# Statement keywords other than SELECT/WITH; used only to word the rejection.
_SQL_COMMANDS = frozenset(
    {
        "ALTER", "ANALYZE", "ATTACH", "BEGIN", "COMMIT", "CREATE", "DELETE", "DETACH",
        "DROP", "END", "EXPLAIN", "INSERT", "PRAGMA", "REINDEX", "RELEASE", "REPLACE",
        "ROLLBACK", "SAVEPOINT", "UPDATE", "UPSERT", "VACUUM", "VALUES",
    }
)

MSG_EMPTY = "Enter one SELECT query."
MSG_TOO_LONG = f"SQL is too long; the limit is {MAX_SQL_LENGTH:,} characters."
MSG_NOT_SELECT = "Only a single read-only SELECT (or WITH ... SELECT) query is allowed."
MSG_MULTIPLE = "Submit exactly one SQL statement."
MSG_UNAUTHORIZED = (
    "Only read-only SELECT queries over customers, orders, and refunds are allowed."
)
MSG_LIMIT = "Query exceeded the execution limit and was stopped."
MSG_TOO_BIG = "Query produced a value larger than the size limit."
MSG_FAILED = "The query could not be executed."


@dataclass
class QueryResult:
    columns: list[str] = field(default_factory=list)
    rows: list[list[ResultCell]] = field(default_factory=list)
    truncated: bool = False
    error: str | None = None


def execute_query(sql: str, fixture: Fixture, *, max_rows: int) -> QueryResult:
    """Run one read-only query against a fresh copy of ``fixture``."""
    problem = _validate_text(sql)
    if problem:
        return QueryResult(error=problem)

    connection = sqlite3.connect(":memory:")
    try:
        seed_database(connection, fixture)
        _lock_down(connection)
        cursor = connection.execute(sql)
        raw = cursor.fetchmany(max_rows + 1)
        columns = [column[0] for column in cursor.description or ()]
        return QueryResult(
            columns=columns,
            rows=[[_json_safe(value) for value in row] for row in raw[:max_rows]],
            truncated=len(raw) > max_rows,
        )
    except sqlite3.Error as exc:
        return QueryResult(error=_public_error(exc))
    except Exception:
        return QueryResult(error=MSG_FAILED)
    finally:
        connection.close()


def _validate_text(sql: str) -> str | None:
    if len(sql) > MAX_SQL_LENGTH:
        return MSG_TOO_LONG
    body = _strip_leading_comments(sql)
    if not body or body == ";":
        return MSG_EMPTY
    keyword = body.split(None, 1)[0].split("(", 1)[0].split(";", 1)[0].upper()
    if keyword in {"SELECT", "WITH"}:
        return None
    if keyword in _SQL_COMMANDS:
        return MSG_NOT_SELECT
    token = "".join(ch for ch in keyword[:20] if ch.isalnum() or ch == "_")
    return f'SQL syntax error near "{token}": queries must start with SELECT or WITH.'


def _strip_leading_comments(sql: str) -> str:
    text = sql.lstrip()
    while True:
        if text.startswith("--"):
            newline = text.find("\n")
            text = "" if newline == -1 else text[newline + 1 :].lstrip()
        elif text.startswith("/*"):
            end = text.find("*/", 2)
            text = "" if end == -1 else text[end + 2 :].lstrip()
        else:
            return text


def _lock_down(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA query_only = ON")
    connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_VALUE_LENGTH)
    connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, MAX_SQL_LENGTH)
    connection.set_authorizer(_authorize)

    deadline = time.monotonic() + MAX_SECONDS
    steps = 0

    def progress() -> int:
        nonlocal steps
        steps += _PROGRESS_INTERVAL
        return int(steps > MAX_VM_STEPS or time.monotonic() > deadline)

    connection.set_progress_handler(progress, _PROGRESS_INTERVAL)


def _authorize(
    action: int, arg1: str | None, arg2: str | None, database: str | None, trigger: str | None
) -> int:
    if action in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        if database == "main" and arg1 in ALLOWED_TABLES:
            return sqlite3.SQLITE_OK
        # SQLite reports a table (or CTE) referenced without extracting any
        # column, e.g. rowid access or COUNT(*), as an empty column name. No
        # values are exposed, and pragma tables are still denied via
        # SQLITE_PRAGMA.
        if arg2 == "":
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        if arg2 is not None and arg2.lower() in ALLOWED_FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_DENY


def _public_error(exc: sqlite3.Error) -> str:
    message = str(exc)
    lowered = message.lower()
    if isinstance(exc, sqlite3.ProgrammingError) and "one statement" in lowered:
        return MSG_MULTIPLE
    if "not authorized" in lowered or "prohibited" in lowered:
        return MSG_UNAUTHORIZED
    if "interrupted" in lowered:
        return MSG_LIMIT
    if "too big" in lowered:
        return MSG_TOO_BIG
    if "readonly" in lowered or "read-only" in lowered:
        return MSG_UNAUTHORIZED
    if isinstance(exc, sqlite3.OperationalError) and message and len(message) <= 200:
        # Ordinary SQL mistakes, e.g. 'near "SELEC": syntax error' or
        # 'no such column: revenue'. These only echo the candidate's own tokens.
        return f"SQL error: {message}"
    return MSG_FAILED


def _json_safe(value: object) -> ResultCell:
    if value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, bytes):
        return value.hex()
    return str(value)
