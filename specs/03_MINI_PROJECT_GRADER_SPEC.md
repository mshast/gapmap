# GapMap — Part 3 of 4: Mini-Project Registry, SQL Execution, and Deterministic Grader

## Codex assignment
Build the technical centerpiece in `apps/api/services/projects/`: one realistic three-step SQL revenue-debugging mini-project with real query execution, hidden fixtures, competency-scored grading, and robust failure handling. Obey Part 4 API/data contracts. Do not allow an LLM to decide pass/fail or run arbitrary Python code.

## Fixed project definition
- ID: `revenue-debug-001`; title: `Investigate an E-commerce Revenue Bug`.
- Fictional e-commerce database tables:
  - `customers(id INTEGER PRIMARY KEY, name TEXT, region TEXT)`
  - `orders(id INTEGER PRIMARY KEY, customer_id INTEGER, amount_cents INTEGER, status TEXT, created_at TEXT)`
  - `refunds(id INTEGER PRIMARY KEY, order_id INTEGER, amount_cents INTEGER)`
- Status rule: ONLY `completed` orders contribute revenue. Net revenue = SUM(completed order amounts) minus SUM(refunds belonging to completed orders). Multiple refunds on one order must not multiply order revenue. Missing refund means zero. Define behavior for customers with missing region as `'Unknown'` and use that consistently in hidden fixtures.
- Monetary comparison: amounts use **integer cents** everywhere (`amount_cents`). Never silently mix dollars and cents.

## Tasks and deliverables
1. **T1: Trace valid orders to regions.** Output `order_id, region, amount_cents` for completed orders. Must join customers and filter status. Sort by `order_id ASC`.
2. **T2: Recalculate gross revenue.** Output `region, gross_revenue_cents` for completed orders, grouped by region, sorted by region ASC; exclude cancelled/pending orders.
3. **T3: Correct net revenue after refunds.** Output `region, net_revenue_cents`, including partial/multiple refunds, no refund, and regions with multiple customers, sorted by region ASC. Avoid double-counting through naive joins.

## Grading and points
100 points total, fixed weighting:
- Joins = 25
- Filtering = 20
- Aggregation = 25
- Refunds/edge cases = 30

Map individual hidden tests to both task and competency; document explicit point allocations that sum to 100, e.g. T1 joins 25 + filtering 10; T2 filtering 10 + aggregation 15; T3 aggregation 10 + refund cases 30. Each test declares exact points, competency, fixture, expected output. Tests must independently cover empty refunds, multiple refunds, cancelled orders, missing region, and duplicate counting. Produce per-competency earned/possible points and pass/fail details with safe diagnostics. Do **not** share hidden fixture rows, canonical SQL, or exact expected results to clients when grading (preview may show visible seed data).

## Verification states
For each competency, set `demonstrated_on_project` only if **all designated tests** for that competency pass; `partially_demonstrated` if at least one passes but not all; `unverified` if none passes. The label is deliberately scoped to this one work sample. Submission history should be retained in session state and newer attempts supersede old results for current score, while optionally keeping an audit history.

## Safe query execution
- Each preview/submission runs in a separate, ephemeral SQLite database seeded with a whitelisted fixture. Never run against user or application data.
- Allow exactly one read-only SELECT statement (a WITH/CTE that resolves to SELECT is fine). No PRAGMA, ATTACH, write operations, extension loading, multiple statements, or arbitrary code. Use SQLite authorizer to deny writes/unsafe operations, plus a SQL parser or robust single-statement validation; simple regex filtering alone is insufficient.
- Limit execution with SQLite progress handler/timeout, fixed max rows, fixed memory/data fixtures, and sanitized errors.
- Reject oversized SQL (e.g. >10,000 chars), statements with side effects, and malicious resource exhaustion.
- Preview returns at most 20 rows from public fixture, error or success; grading executes separately on hidden datasets.
- Score comparison uses canonical column names and row sets/order by task contract; normalize SQLite numeric values consistently (integer cents).

## Required endpoints
- `GET /api/projects/recommended?analysis_id=...` — selected registry project or null with reason.
- `GET /api/projects/{project_id}` — public scenario, schema, instructions, visible seed, tasks (never grader secrets).
- `POST /api/projects/{project_id}/run` — `{session_id,task_id,sql}` -> `{columns,rows,truncated,error}`.
- `POST /api/projects/{project_id}/submit` — `{session_id,task_id,sql}` -> `{task_score, competency_scores, public_test_feedback, submission_id}` and update session evidence.

## Implementation structure
- `registry.py` project metadata and competency IDs.
- `fixtures.py` deterministic fixture setup; public + hidden.
- `executor.py` safe read-only SQLite execution.
- `grading.py` oracle answers independent from the candidate's SQL, explicit test configurations.
- `routes.py` API endpoints.
- `tests/test_grading.py` positive, negative, malicious, and edge-case tests.

## Acceptance checks
- [ ] Reference implementation achieves exactly 100/100 on all hidden cases.
- [ ] Query ignoring refund gets refund tests wrong and cannot score 100.
- [ ] Naive order-refunds join that duplicates gross revenue fails multi-refund fixture.
- [ ] `DROP TABLE`, multi-statement, ATTACH, PRAGMA, recursive runaway query rejected safely.
- [ ] Runtime/SQL error returns useful, non-sensitive feedback; service remains healthy.
- [ ] Different logically correct SQL solutions are accepted based on outputs (not string equality).
- [ ] New assessment results update session evidence per Part 4.
