"""Deterministic fallback briefs for every supported skill family.

These are deliberately specific: a product, an operating scenario, bounded
inputs and outputs, three milestones with completion checks, tests, and
evidence. They are labeled ``source="fallback"`` and never claim grading.
"""

from gapmap.apps.api.contracts import BriefMilestone, ProjectBrief, Requirement
from gapmap.apps.api.services.briefs.selection import family_for
from gapmap.apps.api.services.projects.registry import (
    PROJECT_ID,
    PROJECT_TITLE,
    SCENARIO as SQL_SCENARIO,
)

# title, work, acceptance criteria, tests, evidence
MilestoneSpec = tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], str]


def fallback_plan(requirement: Requirement) -> ProjectBrief:
    return _BUILDERS[family_for(requirement)](requirement)


def _build(
    requirement: Requirement,
    *,
    title: str,
    summary: str,
    scenario: str,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
    constraints: tuple[str, ...],
    deliverables: tuple[str, ...],
    milestones: tuple[MilestoneSpec, ...],
    runnable_project_id: str | None = None,
) -> ProjectBrief:
    return ProjectBrief(
        id=f"plan-{requirement.id}",
        requirement_id=requirement.id,
        title=title,
        summary=summary,
        job_quote=requirement.job_quote,
        skills=requirement.skill_ids[:8],
        scenario=scenario,
        inputs=list(inputs),
        outputs=list(outputs),
        constraints=list(constraints),
        deliverables=list(deliverables),
        milestones=[
            BriefMilestone(
                title=item[0],
                work=list(item[1]),
                acceptance_criteria=list(item[2]),
                tests=list(item[3]),
                evidence=item[4],
            )
            for item in milestones
        ],
        source="fallback",
        runnable_project_id=runnable_project_id,
    )


def _python(requirement: Requirement) -> ProjectBrief:
    label = requirement.label
    return _build(
        requirement,
        title=f"Invoice Reconciliation Tool — {label}",
        summary=(
            "A command-line tool that reconciles a month of invoice exports against a "
            "payments ledger and reports every mismatch. It is built for one analyst who "
            "checks these files by hand, turning a manual afternoon into a tested run."
        ),
        scenario=(
            f"The posting asks for {label.lower()}. You join a small finance-ops team that "
            "closes the books from two CSV exports each month; mismatches surface late and "
            "the totals are not trusted. Build the tool the analyst keeps on their laptop."
        ),
        inputs=(
            "Two CSV exports, invoices and payments, with 20–50 sample rows you create",
            "A config file naming the key column, amount column, and currency",
            "Edge fixtures: duplicate ids, missing ids, fractional amounts",
        ),
        outputs=(
            "A reconciled CSV classifying each row as matched, unpaid, or overpaid",
            "A one-page summary with counts and totals per class",
            "A non-zero exit code when mismatches exceed the configured threshold",
        ),
        constraints=(
            "Python 3.12 standard library only; no hosted services",
            "Byte-identical output for the same inputs",
            "Under two seconds for 10,000 rows on a laptop",
            "Malformed input produces a readable error, never a stack trace",
        ),
        deliverables=(
            "The CLI and a README with one-command setup",
            "A pytest suite covering a clean run and three failure cases",
            "Sample fixtures a reviewer can run immediately",
            "A two-minute recording of a failing then passing run",
        ),
        milestones=(
            (
                "Parse and validate both exports",
                (
                    "Load both CSVs against an explicit schema and reject rows that fail it",
                    "Normalize ids and integer cents before any comparison",
                ),
                (
                    "A clean fixture loads with zero warnings",
                    "A malformed row reports its line number and stops the run",
                ),
                (
                    "Happy path: a 20-row fixture parses into typed records",
                    "Edge: a row with a missing id is rejected with a readable message",
                ),
                "The validation test output and the README input-format section.",
            ),
            (
                "Reconcile and report",
                (
                    "Join invoices to payments by id and classify matched, unpaid, and overpaid",
                    "Write the reconciled CSV and a summary with totals",
                ),
                (
                    "The sample month reports exactly the expected mismatch count",
                    "Every unmatched invoice appears exactly once in the output",
                ),
                (
                    "Happy path: a month with two mismatches reports exactly those two",
                    "Edge: a duplicated payment id is counted once and flagged",
                ),
                "The sample reconciled CSV and summary produced by one command.",
            ),
            (
                "Package it for the analyst",
                (
                    "Add a CLI with input, output, and threshold options",
                    "Document setup, exit codes, and how to add fixtures",
                ),
                (
                    "A reviewer can run it from a clean checkout using only the README",
                    "Exceeding the threshold exits non-zero and explains why",
                ),
                (
                    "Happy path: the documented command reproduces the sample summary",
                    "Failure: an unreadable path exits with guidance, not a traceback",
                ),
                "The README, the recording, and the passing test run.",
            ),
        ),
    )


def _react(requirement: Requirement) -> ProjectBrief:
    label = requirement.label
    return _build(
        requirement,
        title=f"Incident Review Console — {label}",
        summary=(
            "A single-page console for triaging incident reports: a filterable queue on the "
            "left, a detail pane on the right, and honest loading, empty, and error states. "
            "It targets an on-call engineer who must review reports quickly."
        ),
        scenario=(
            f"The posting asks for {label.lower()}. An on-call engineer currently triages "
            "incidents from a long shared document and loses their place whenever the list "
            "changes. Build the console they keep open during a shift, against a local fixture."
        ),
        inputs=(
            "A JSON fixture of 200 incident reports with severity, status, and timestamps",
            "A severity filter, a search field, and a sort control",
            "A simulated failing request so the error state is real",
        ),
        outputs=(
            "A filterable queue showing counts per severity",
            "A detail pane for the selected report with its metadata",
            "Visible loading, empty, error, and retry states",
        ),
        constraints=(
            "Keyboard navigable with a visible focus ring",
            "Usable down to a 1024px-wide window",
            "React state and reducers only; no state library",
            "200 rows without dropped input frames",
        ),
        deliverables=(
            "The app and a README with commands",
            "Component tests covering loading, error, empty, and filtering",
            "A short recording of keyboard-only triage",
        ),
        milestones=(
            (
                "Render the queue with real states",
                (
                    "Model the fixture and build an explicit loading, empty, error, and ready state",
                    "Render the queue with stable keys and accessible row actions",
                ),
                (
                    "The first paint shows a skeleton, never a blank panel",
                    "A rejected request shows an error with a working retry",
                ),
                (
                    "Happy path: three reports render in severity order",
                    "Failure: a rejected fetch shows the error state and retry",
                ),
                "The component test output and a screenshot of all four states.",
            ),
            (
                "Add filtering and selection",
                (
                    "Filter by severity and search text with counts that update live",
                    "Select a report by mouse and keyboard and keep the pane in sync",
                ),
                (
                    "Filters combine and clear without a full re-render",
                    "Arrow keys and Enter move and open a report",
                ),
                (
                    "Happy path: a severity filter narrows the queue to the right rows",
                    "Edge: a filter with no matches shows the empty state, not an error",
                ),
                "The filtering tests and the keyboard-only recording.",
            ),
            (
                "Polish and prove it",
                (
                    "Add focus management, aria labels, and a reduced-motion path",
                    "Measure render time for 200 rows and document the result",
                ),
                (
                    "A keyboard-only user can triage a report end to end",
                    "The measured render stays under 150 ms on the fixture",
                ),
                (
                    "Happy path: the documented triage flow passes in the test runner",
                    "Failure: an invalid fixture entry is handled without crashing",
                ),
                "The README measurements and the passing accessibility checks.",
            ),
        ),
    )


def _docker(requirement: Requirement) -> ProjectBrief:
    label = requirement.label
    return _build(
        requirement,
        title=f"Reproducible Service Container — {label}",
        summary=(
            "A production-shaped container for a small HTTP service: a multi-stage build, a "
            "non-root user, a health check, and one command to run. It is built for a team "
            "that cannot reproduce a bug because each laptop differs."
        ),
        scenario=(
            f"The posting asks for {label.lower()}. The team ships a small internal service "
            "that works on one laptop and fails on another. Build the image and runbook that "
            "make the service reproducible for everyone, without changing its behavior."
        ),
        inputs=(
            "A small HTTP service you write, with one JSON endpoint and startup config",
            "A .env.example listing every required variable",
            "A copy of the bug on a clean machine to reproduce",
        ),
        outputs=(
            "A single image tag that runs the service locally",
            "A /health endpoint and structured startup logs",
            "A documented one-command run with exit codes",
        ),
        constraints=(
            "Multi-stage build with pinned base-image versions",
            "Non-root runtime user and no secrets baked into layers",
            "Image under 200 MB; health check returns within two seconds",
            "Configuration comes from the environment, never the image",
        ),
        deliverables=(
            "Dockerfile, compose file, and .dockerignore",
            "A README covering build, run, health, and recovery",
            "A small CI script that builds and probes the container",
        ),
        milestones=(
            (
                "Build a reproducible image",
                (
                    "Write the service, pin a slim base image, and add a multi-stage build",
                    "Copy only runtime artifacts and set a non-root user",
                ),
                (
                    "A clean clone builds the same image tag with no manual steps",
                    "The container starts and answers its endpoint",
                ),
                (
                    "Happy path: build then run answers the JSON endpoint",
                    "Failure: a build with a missing lockfile fails with a clear message",
                ),
                "The build log and the successful local request.",
            ),
            (
                "Harden and observe",
                (
                    "Add a health check, read-only filesystem, and bounded memory",
                    "Log startup configuration without printing secrets",
                ),
                (
                    "The health check reports unhealthy when the service is stopped",
                    "No secret value appears in image history or logs",
                ),
                (
                    "Happy path: the health check turns healthy within two seconds",
                    "Edge: missing required config exits with a readable error",
                ),
                "The health-check output and the secret scan result.",
            ),
            (
                "Operate and document",
                (
                    "Add compose config and a CI probe script",
                    "Write the runbook: build, run, inspect, recover",
                ),
                (
                    "A reviewer runs the service from the README alone",
                    "The CI script fails when the health probe fails",
                ),
                (
                    "Happy path: compose up serves the endpoint",
                    "Failure: a stopped container is reported by the probe",
                ),
                "The runbook, CI output, and the recorded recovery step.",
            ),
        ),
    )


def _dsa(requirement: Requirement) -> ProjectBrief:
    label = requirement.label
    return _build(
        requirement,
        title=f"Route Planning Benchmark — {label}",
        summary=(
            "Two shortest-path implementations over a small city graph, plus a benchmark "
            "that explains when each wins. It targets a reviewer who wants evidence you can "
            "reason about complexity and measure on real inputs."
        ),
        scenario=(
            f"The posting asks for {label.lower()}. A delivery team needs to estimate travel "
            "time between depots and is deciding between a simple search and a guided one. "
            "Build both, measure them, and write down when each is the right choice."
        ),
        inputs=(
            "A graph fixture of 50 nodes and 150 weighted edges",
            "Twenty origin–destination pairs, including one unreachable pair",
            "Size knobs that scale the graph to 5,000 nodes",
        ),
        outputs=(
            "Shortest routes and distances for each pair",
            "A timing table with the measured growth per input size",
            "A short write-up naming the complexity and the crossover point",
        ),
        constraints=(
            "No third-party graph library; the structures are yours",
            "Documented time and space complexity for each approach",
            "Deterministic results for the same fixture and seed",
            "Invalid input, such as a negative weight, is rejected explicitly",
        ),
        deliverables=(
            "Both implementations with type hints",
            "A pytest suite over shortest paths and failure cases",
            "A benchmark script that writes the timing table",
            "A README with the complexity write-up",
        ),
        milestones=(
            (
                "Model the graph and ship a baseline",
                (
                    "Implement the adjacency structure and a priority-queue shortest path",
                    "Reconstruct and return the path, not only the distance",
                ),
                (
                    "Every reachable pair returns the documented shortest distance",
                    "An unreachable pair returns no route without hanging",
                ),
                (
                    "Happy path: a known five-node graph returns the expected route",
                    "Failure: a negative edge weight is rejected before the search",
                ),
                "The baseline tests and the route output for the sample graph.",
            ),
            (
                "Add a guided search and compare",
                (
                    "Implement a heuristic-guided search with an admissible heuristic",
                    "Assert both approaches return identical distances on the fixtures",
                ),
                (
                    "Results match the baseline on every pair in the fixture",
                    "The guided search expands fewer nodes on the same pair",
                ),
                (
                    "Happy path: both approaches agree on all 20 pairs",
                    "Edge: a zero-weight edge is handled without a loop",
                ),
                "The agreement test and the node-expansion counts.",
            ),
            (
                "Benchmark and explain",
                (
                    "Script the timing runs across input sizes and write the table",
                    "Document complexity, the crossover point, and the limits",
                ),
                (
                    "The benchmark reproduces the README table",
                    "The write-up states when the simpler approach is preferable",
                ),
                (
                    "Happy path: the script regenerates the table in under a minute",
                    "Failure: a malformed graph file exits with a clear error",
                ),
                "The generated timing table and the complexity write-up.",
            ),
        ),
    )


def _other(requirement: Requirement) -> ProjectBrief:
    label = requirement.label
    return _build(
        requirement,
        title=f"Sample Review Desk — {label}",
        summary=(
            "A small local tool that turns one recurring review into a checklist-driven desk "
            "with an exported decision log. It targets a team that reviews the same kind of "
            "item repeatedly and needs a defensible record of each decision."
        ),
        scenario=(
            f"The posting asks for {label.lower()}. Pick one review your target team repeats "
            "weekly, model twenty realistic items from their domain, and build the desk that "
            "applies a written checklist and records why each item passed or failed."
        ),
        inputs=(
            "Twenty sample items in JSON or CSV, invented from the team's domain",
            "A rules file with five checks, each with a pass and fail message",
            "Reviewer notes for two intentionally ambiguous items",
        ),
        outputs=(
            "A reviewed queue with pass, fail, or needs-review per item",
            "A per-rule breakdown explaining every failure",
            "An exported decision log with item id, rule, outcome, and reason",
        ),
        constraints=(
            "Local data only; no accounts, uploads, or external services",
            "Rules live in one inspectable file, not in code",
            "Every decision carries a human-readable reason",
            "The same input and rules produce the same log",
        ),
        deliverables=(
            "The desk with a README and setup command",
            "Tests covering a clean run, an ambiguous item, and an invalid rule",
            "The exported sample decision log",
            "A two-minute walkthrough recording",
        ),
        milestones=(
            (
                "Model the items and fixtures",
                (
                    "Define the item schema and write twenty realistic fixtures",
                    "Load and validate the fixtures with readable errors",
                ),
                (
                    "The fixture set loads with zero unexpected warnings",
                    "An item missing a required field names the field and the row",
                ),
                (
                    "Happy path: twenty items load into typed records",
                    "Edge: a duplicate item id is flagged, not silently merged",
                ),
                "The fixture file, the schema, and the validation test output.",
            ),
            (
                "Apply the checklist",
                (
                    "Load the five rules and evaluate each item in a deterministic order",
                    "Record a reason for every pass and fail",
                ),
                (
                    "Each rule fires on exactly the fixtures designed to trigger it",
                    "The ambiguous item is marked needs-review, not guessed",
                ),
                (
                    "Happy path: the sample set produces the expected pass counts",
                    "Failure: a rule with a missing field is rejected with its name",
                ),
                "The results table and the exported decision log.",
            ),
            (
                "Ship the desk and the record",
                (
                    "Build the review view or CLI and the log export",
                    "Write the README that explains the checklist and its limits",
                ),
                (
                    "A reviewer can load the fixtures and export the log in one command",
                    "The README names one limitation of the checklist",
                ),
                (
                    "Happy path: the documented command reproduces the sample log",
                    "Failure: an unreadable rules file exits with guidance",
                ),
                "The recording, the README, and the exported log.",
            ),
        ),
    )


def _sql(requirement: Requirement) -> ProjectBrief:
    return _build(
        requirement,
        title=PROJECT_TITLE,
        summary=(
            "A three-task SQL investigation into a revenue dashboard that disagrees with the "
            "ledger. You trace completed orders to regions, recompute gross revenue, then "
            "correct net revenue after refunds; the hidden grader checks each step."
        ),
        scenario=SQL_SCENARIO,
        inputs=(
            "The customers, orders, and refunds tables in the visible preview fixture",
            "The three starter queries, including the current dashboard query",
            "The documented business rules for status, refunds, and missing regions",
        ),
        outputs=(
            "One completed order per row with its customer region for task t1",
            "Gross revenue in integer cents per region for task t2",
            "Net revenue in integer cents per region after refunds for task t3",
        ),
        constraints=(
            "Only completed orders contribute revenue",
            "A missing or empty region is reported as 'Unknown'",
            "Amounts stay in integer cents; never convert to dollars",
            "Each submission is one read-only SELECT or WITH query",
        ),
        deliverables=(
            "The three corrected queries saved with their results",
            "A short README explaining the bug in the original dashboard query",
            "The graded feedback for each task",
        ),
        milestones=(
            (
                "Trace valid orders to their regions",
                (
                    "Join orders to customers on the customer id",
                    "Keep only completed orders and map a missing region to 'Unknown'",
                ),
                (
                    "Each completed order appears once with its region",
                    "The rows are sorted by order id ascending",
                ),
                (
                    "Happy path: completed orders only, with their regions",
                    "Edge: a NULL or empty region is reported as 'Unknown'",
                ),
                "The t1 result table and the joins/filtering feedback.",
            ),
            (
                "Recalculate gross revenue",
                (
                    "Group completed orders by region and sum integer cents",
                    "Exclude cancelled and pending orders from the total",
                ),
                (
                    "Every region with completed revenue appears once",
                    "The totals match the ledger for the preview fixture",
                ),
                (
                    "Happy path: gross totals match the expected per-region sums",
                    "Edge: a region with only cancelled orders is absent",
                ),
                "The t2 result table and the aggregation feedback.",
            ),
            (
                "Correct net revenue after refunds",
                (
                    "Aggregate refunds per order before joining them to completed orders",
                    "Subtract the refund total without repeating an order amount",
                ),
                (
                    "Orders without refunds keep their full amount",
                    "Multiple refunds reduce revenue once, never twice",
                ),
                (
                    "Happy path: net revenue matches the corrected dashboard",
                    "Edge: several refunds on one order are not double-counted",
                ),
                "The t3 result table and the refund edge-case feedback.",
            ),
        ),
        runnable_project_id=PROJECT_ID,
    )


_BUILDERS = {
    "python": _python,
    "react": _react,
    "docker": _docker,
    "dsa": _dsa,
    "other": _other,
    "sql": _sql,
}
