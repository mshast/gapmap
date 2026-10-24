"""Deterministic fixture datasets for the revenue debugging project.

The public fixture is the preview dataset candidates may query freely. Hidden
fixtures are used only by the grader and must never be returned to clients;
each one isolates a single edge case so a failure points at one competency.
"""

import sqlite3
from dataclasses import dataclass


CustomerRow = tuple[int, str, str | None]
OrderRow = tuple[int, int, int, str, str]
RefundRow = tuple[int, int, int]

SCHEMA_DDL = (
    "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, region TEXT)",
    "CREATE TABLE orders ("
    "id INTEGER PRIMARY KEY, customer_id INTEGER, amount_cents INTEGER, "
    "status TEXT, created_at TEXT)",
    "CREATE TABLE refunds (id INTEGER PRIMARY KEY, order_id INTEGER, amount_cents INTEGER)",
)


@dataclass(frozen=True)
class Fixture:
    name: str
    customers: tuple[CustomerRow, ...]
    orders: tuple[OrderRow, ...]
    refunds: tuple[RefundRow, ...] = ()


def seed_database(connection: sqlite3.Connection, fixture: Fixture) -> None:
    """Create the project schema and insert one fixture's rows."""
    for statement in SCHEMA_DDL:
        connection.execute(statement)
    connection.executemany("INSERT INTO customers VALUES (?, ?, ?)", fixture.customers)
    connection.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", fixture.orders)
    connection.executemany("INSERT INTO refunds VALUES (?, ?, ?)", fixture.refunds)
    connection.commit()


PUBLIC_FIXTURE = Fixture(
    name="public_preview",
    customers=(
        (1, "Ada", "North"),
        (2, "Ben", "South"),
        (3, "Cy", None),
    ),
    orders=(
        (101, 1, 5000, "completed", "2026-03-01"),
        (102, 2, 2500, "pending", "2026-03-02"),
        (103, 1, 1200, "completed", "2026-03-02"),
        (104, 3, 800, "completed", "2026-03-03"),
        (105, 2, 3000, "cancelled", "2026-03-04"),
    ),
    refunds=((1, 103, 200),),
)

_BASELINE = Fixture(
    name="baseline",
    customers=(
        (1, "Avery", "East"),
        (2, "Blake", "West"),
        (3, "Casey", "East"),
        (4, "Drew", "North"),
    ),
    orders=(
        (1, 1, 10000, "completed", "2026-01-03"),
        (2, 2, 4500, "completed", "2026-01-04"),
        (3, 3, 7000, "completed", "2026-01-05"),
        (4, 4, 2000, "pending", "2026-01-06"),
        (5, 2, 3300, "completed", "2026-01-07"),
    ),
    refunds=((1, 3, 1500),),
)

# Refunds table is empty: an INNER JOIN to refunds loses every order.
_NO_REFUNDS = Fixture(
    name="no_refunds",
    customers=(
        (1, "Elliot", "Central"),
        (2, "Frankie", "Coastal"),
    ),
    orders=(
        (10, 1, 1999, "completed", "2026-02-01"),
        (11, 2, 2501, "completed", "2026-02-01"),
        (12, 1, 999, "completed", "2026-02-02"),
        (13, 2, 400, "cancelled", "2026-02-03"),
    ),
)

# Orders 20 and 21 have several refunds each: a naive orders-refunds join
# repeats their amounts once per refund row.
_MULTIPLE_REFUNDS = Fixture(
    name="multiple_refunds",
    customers=(
        (1, "Gale", "North"),
        (2, "Harper", "South"),
        (3, "Indy", "North"),
    ),
    orders=(
        (20, 1, 10000, "completed", "2026-02-10"),
        (21, 2, 8000, "completed", "2026-02-11"),
        (22, 3, 6000, "completed", "2026-02-12"),
        (23, 2, 1000, "completed", "2026-02-13"),
    ),
    refunds=(
        (1, 20, 1000),
        (2, 20, 2500),
        (3, 20, 500),
        (4, 21, 1000),
        (5, 21, 1000),
    ),
)

# Pending and cancelled orders, some carrying refunds that must not count.
_CANCELLED_ORDERS = Fixture(
    name="cancelled_orders",
    customers=(
        (1, "Jules", "East"),
        (2, "Kai", "West"),
    ),
    orders=(
        (30, 1, 5000, "completed", "2026-02-20"),
        (31, 1, 4000, "cancelled", "2026-02-20"),
        (32, 2, 3000, "pending", "2026-02-21"),
        (33, 2, 6000, "completed", "2026-02-21"),
        (34, 1, 2000, "cancelled", "2026-02-22"),
        (35, 2, 1500, "completed", "2026-02-23"),
    ),
    refunds=(
        (1, 31, 4000),
        (2, 32, 500),
        (3, 33, 1000),
    ),
)

# NULL and empty-string regions both report as 'Unknown'.
_MISSING_REGION = Fixture(
    name="missing_region",
    customers=(
        (1, "Lane", None),
        (2, "Morgan", ""),
        (3, "Noor", "South"),
    ),
    orders=(
        (40, 1, 2500, "completed", "2026-03-05"),
        (41, 2, 1500, "completed", "2026-03-05"),
        (42, 3, 4000, "completed", "2026-03-06"),
        (43, 1, 700, "pending", "2026-03-07"),
    ),
    refunds=((1, 41, 500),),
)

# Partial and full refunds; West is refunded down to exactly zero, and order
# 53 has no refund so an INNER JOIN to refunds drops it.
_PARTIAL_REFUNDS = Fixture(
    name="partial_refunds",
    customers=(
        (1, "Parker", "East"),
        (2, "Quinn", "West"),
        (3, "Reese", "West"),
    ),
    orders=(
        (50, 1, 9000, "completed", "2026-03-10"),
        (51, 2, 3000, "completed", "2026-03-10"),
        (52, 3, 2000, "completed", "2026-03-11"),
        (53, 1, 1000, "completed", "2026-03-12"),
    ),
    refunds=(
        (1, 50, 4500),
        (2, 51, 3000),
        (3, 52, 2000),
    ),
)

# Several customers share a region, mixed with refunds and excluded statuses.
_MULTI_CUSTOMER_REGION = Fixture(
    name="multi_customer_region",
    customers=(
        (1, "Sam", "Central"),
        (2, "Tate", "Central"),
        (3, "Uma", "Central"),
        (4, "Vic", "Mountain"),
        (5, "Wren", "Mountain"),
        (6, "Xan", "Pacific"),
    ),
    orders=(
        (60, 1, 1200, "completed", "2026-04-01"),
        (61, 2, 3400, "completed", "2026-04-01"),
        (62, 3, 5600, "completed", "2026-04-02"),
        (63, 4, 7800, "completed", "2026-04-02"),
        (64, 5, 900, "completed", "2026-04-03"),
        (65, 6, 2100, "pending", "2026-04-03"),
        (66, 2, 1100, "cancelled", "2026-04-04"),
        (67, 6, 4300, "completed", "2026-04-05"),
    ),
    refunds=(
        (1, 61, 400),
        (2, 61, 600),
        (3, 63, 800),
        (4, 66, 1100),
    ),
)

HIDDEN_FIXTURES: dict[str, Fixture] = {
    fixture.name: fixture
    for fixture in (
        _BASELINE,
        _NO_REFUNDS,
        _MULTIPLE_REFUNDS,
        _CANCELLED_ORDERS,
        _MISSING_REGION,
        _PARTIAL_REFUNDS,
        _MULTI_CUSTOMER_REGION,
    )
}
