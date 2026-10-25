import type { ProjectBrief, ProjectBriefs } from "@/lib/types";

type Milestone = ProjectBrief["milestones"][number];

function milestone(
  title: string,
  work: string[],
  acceptance: string[],
  tests: string[],
  evidence: string,
): Milestone {
  return { title, work, acceptance_criteria: acceptance, tests, evidence };
}

const sqlPlan: ProjectBrief = {
  id: "plan-req-sql",
  requirement_id: "req-sql",
  title: "Investigate an E-commerce Revenue Bug",
  summary:
    "A three-task SQL investigation into a revenue dashboard that disagrees with the ledger. You trace completed orders to regions, recompute gross revenue, then correct net revenue after refunds.",
  job_quote: "Experience with SQL databases is required.",
  skills: ["sql_joins", "sql_filtering", "sql_aggregation"],
  scenario:
    "Finance reports that the regional revenue dashboard disagrees with the ledger. The current query counts every order status and joins refunds in a way that repeats order amounts. Build the trustworthy queries and document the bug.",
  inputs: [
    "The customers, orders, and refunds tables in the preview fixture",
    "The three starter queries, including the current dashboard query",
    "The business rules for status, refunds, and missing regions",
  ],
  outputs: [
    "One completed order per row with its customer region",
    "Gross revenue in integer cents per region",
    "Net revenue in integer cents per region after refunds",
  ],
  constraints: [
    "Only completed orders contribute revenue",
    "A missing or empty region is reported as 'Unknown'",
    "Amounts stay in integer cents; never convert to dollars",
  ],
  deliverables: [
    "The three corrected queries saved with their results",
    "A short README explaining the original bug",
    "The graded feedback for each task",
  ],
  milestones: [
    milestone(
      "Trace valid orders to their regions",
      [
        "Join orders to customers on the customer id",
        "Keep only completed orders and map a missing region to 'Unknown'",
      ],
      [
        "Each completed order appears once with its region",
        "Rows are sorted by order id ascending",
      ],
      [
        "Happy path: completed orders only, with their regions",
        "Edge: a NULL or empty region is reported as 'Unknown'",
      ],
      "The t1 result table and the joins/filtering feedback.",
    ),
    milestone(
      "Recalculate gross revenue",
      [
        "Group completed orders by region and sum integer cents",
        "Exclude cancelled and pending orders from the total",
      ],
      [
        "Every region with completed revenue appears once",
        "Totals match the ledger for the preview fixture",
      ],
      [
        "Happy path: per-region gross totals match the expected sums",
        "Edge: a region with only cancelled orders is absent",
      ],
      "The t2 result table and the aggregation feedback.",
    ),
    milestone(
      "Correct net revenue after refunds",
      [
        "Aggregate refunds per order before joining them to completed orders",
        "Subtract the refund total without repeating an order amount",
      ],
      [
        "Orders without refunds keep their full amount",
        "Multiple refunds reduce revenue once, never twice",
      ],
      [
        "Happy path: net revenue matches the corrected dashboard",
        "Edge: several refunds on one order are not double-counted",
      ],
      "The t3 result table and the refund edge-case feedback.",
    ),
  ],
  source: "fallback",
  runnable_project_id: "revenue-debug-001",
};

const pythonPlan: ProjectBrief = {
  id: "plan-req-python",
  requirement_id: "req-python",
  title: "Invoice Reconciliation Tool — Python programming",
  summary:
    "A command-line tool that reconciles a month of invoice exports against a payments ledger and reports every mismatch. It is built for one analyst who checks these files by hand, turning a manual afternoon into a tested run.",
  job_quote: "Experience with Python is required.",
  skills: ["python"],
  scenario:
    "The posting asks for Python programming. You join a small finance-ops team that closes the books from two CSV exports each month; mismatches surface late and the totals are not trusted. Build the tool the analyst keeps on their laptop, with no service to deploy.",
  inputs: [
    "Two CSV exports, invoices and payments, with 20–50 sample rows you create",
    "A config file naming the key column, amount column, and currency",
    "Edge fixtures: duplicate ids, missing ids, fractional amounts",
  ],
  outputs: [
    "A reconciled CSV classifying each row as matched, unpaid, or overpaid",
    "A one-page summary with counts and totals per class",
    "A non-zero exit code when mismatches exceed the configured threshold",
  ],
  constraints: [
    "Python 3.12 standard library only; no hosted services",
    "Byte-identical output for the same inputs",
    "Under two seconds for 10,000 rows",
    "Malformed input produces a readable error, never a stack trace",
  ],
  deliverables: [
    "The CLI and a README with one-command setup",
    "A pytest suite covering a clean run and three failure cases",
    "Sample fixtures a reviewer can run immediately",
    "A two-minute recording of a failing then passing run",
  ],
  milestones: [
    milestone(
      "Parse and validate both exports",
      [
        "Load both CSVs against an explicit schema and reject rows that fail it",
        "Normalize ids and integer cents before any comparison",
      ],
      [
        "A clean fixture loads with zero warnings",
        "A malformed row reports its line number and stops the run",
      ],
      [
        "Happy path: a 20-row fixture parses into typed records",
        "Edge: a row with a missing id is rejected with a readable message",
      ],
      "The validation test output and the README input-format section.",
    ),
    milestone(
      "Reconcile and report",
      [
        "Join invoices to payments by id and classify matched, unpaid, and overpaid",
        "Write the reconciled CSV and a summary with totals",
      ],
      [
        "The sample month reports exactly the expected mismatch count",
        "Every unmatched invoice appears exactly once in the output",
      ],
      [
        "Happy path: a month with two mismatches reports exactly those two",
        "Edge: a duplicated payment id is counted once and flagged",
      ],
      "The sample reconciled CSV and summary produced by one command.",
    ),
    milestone(
      "Package it for the analyst",
      [
        "Add a CLI with input, output, and threshold options",
        "Document setup, exit codes, and how to add fixtures",
      ],
      [
        "A reviewer can run it from a clean checkout using only the README",
        "Exceeding the threshold exits non-zero and explains why",
      ],
      [
        "Happy path: the documented command reproduces the sample summary",
        "Failure: an unreadable path exits with guidance, not a traceback",
      ],
      "The README, the recording, and the passing test run.",
    ),
  ],
  source: "fallback",
  runnable_project_id: null,
};

const reactPlan: ProjectBrief = {
  id: "plan-req-react",
  requirement_id: "req-react",
  title: "Incident Review Console — React user interfaces",
  summary:
    "A single-page console for triaging incident reports: a filterable queue on the left, a detail pane on the right, and honest loading, empty, and error states. It targets an on-call engineer during a shift.",
  job_quote: "Experience building user interfaces with React is preferred.",
  skills: ["react"],
  scenario:
    "An on-call engineer currently triages incidents from a long shared document and loses their place whenever the list changes. Build the console they keep open during a shift, against a local fixture.",
  inputs: [
    "A JSON fixture of 200 incident reports with severity, status, and timestamps",
    "A severity filter, a search field, and a sort control",
    "A simulated failing request so the error state is real",
  ],
  outputs: [
    "A filterable queue showing counts per severity",
    "A detail pane for the selected report with its metadata",
    "Visible loading, empty, error, and retry states",
  ],
  constraints: [
    "Keyboard navigable with a visible focus ring",
    "Usable down to a 1024px-wide window",
    "React state and reducers only; no state library",
    "200 rows without dropped input frames",
  ],
  deliverables: [
    "The app and a README with commands",
    "Component tests covering loading, error, empty, and filtering",
    "A short recording of keyboard-only triage",
  ],
  milestones: [
    milestone(
      "Render the queue with real states",
      [
        "Model the fixture and an explicit loading, empty, error, and ready state",
        "Render the queue with stable keys and accessible row actions",
      ],
      [
        "The first paint shows a skeleton, never a blank panel",
        "A rejected request shows an error with a working retry",
      ],
      [
        "Happy path: three reports render in severity order",
        "Failure: a rejected fetch shows the error state and retry",
      ],
      "The component test output and a screenshot of all four states.",
    ),
    milestone(
      "Add filtering and selection",
      [
        "Filter by severity and search text with counts that update live",
        "Select a report by mouse and keyboard and keep the pane in sync",
      ],
      [
        "Filters combine and clear without a full re-render",
        "Arrow keys and Enter move and open a report",
      ],
      [
        "Happy path: a severity filter narrows the queue to the right rows",
        "Edge: a filter with no matches shows the empty state, not an error",
      ],
      "The filtering tests and the keyboard-only recording.",
    ),
    milestone(
      "Polish and prove it",
      [
        "Add focus management, aria labels, and a reduced-motion path",
        "Measure render time for 200 rows and document the result",
      ],
      [
        "A keyboard-only user can triage a report end to end",
        "The measured render stays under 150 ms on the fixture",
      ],
      [
        "Happy path: the documented triage flow passes in the test runner",
        "Failure: an invalid fixture entry is handled without crashing",
      ],
      "The README measurements and the passing accessibility checks.",
    ),
  ],
  source: "fallback",
  runnable_project_id: null,
};

const dockerPlan: ProjectBrief = {
  id: "plan-req-docker",
  requirement_id: "req-docker",
  title: "Reproducible Service Container — Docker containers",
  summary:
    "A production-shaped container for a small HTTP service: a multi-stage build, a non-root user, a health check, and one command to run. Built for a team that cannot reproduce a bug because each laptop differs.",
  job_quote: "Familiarity with Docker containers is preferred.",
  skills: ["docker"],
  scenario:
    "The team ships a small internal service that works on one laptop and fails on another. Build the image and runbook that make the service reproducible for everyone, without changing its behavior.",
  inputs: [
    "A small HTTP service you write, with one JSON endpoint and startup config",
    "A .env.example listing every required variable",
    "A copy of the bug on a clean machine to reproduce",
  ],
  outputs: [
    "A single image tag that runs the service locally",
    "A /health endpoint and structured startup logs",
    "A documented one-command run with exit codes",
  ],
  constraints: [
    "Multi-stage build with pinned base-image versions",
    "Non-root runtime user and no secrets baked into layers",
    "Image under 200 MB; health check returns within two seconds",
    "Configuration comes from the environment, never the image",
  ],
  deliverables: [
    "Dockerfile, compose file, and .dockerignore",
    "A README covering build, run, health, and recovery",
    "A small CI script that builds and probes the container",
  ],
  milestones: [
    milestone(
      "Build a reproducible image",
      [
        "Write the service, pin a slim base image, and add a multi-stage build",
        "Copy only runtime artifacts and set a non-root user",
      ],
      [
        "A clean clone builds the same image tag with no manual steps",
        "The container starts and answers its endpoint",
      ],
      [
        "Happy path: build then run answers the JSON endpoint",
        "Failure: a build with a missing lockfile fails with a clear message",
      ],
      "The build log and the successful local request.",
    ),
    milestone(
      "Harden and observe",
      [
        "Add a health check, read-only filesystem, and bounded memory",
        "Log startup configuration without printing secrets",
      ],
      [
        "The health check reports unhealthy when the service is stopped",
        "No secret value appears in image history or logs",
      ],
      [
        "Happy path: the health check turns healthy within two seconds",
        "Edge: missing required config exits with a readable error",
      ],
      "The health-check output and the secret scan result.",
    ),
    milestone(
      "Operate and document",
      [
        "Add compose config and a CI probe script",
        "Write the runbook: build, run, inspect, recover",
      ],
      [
        "A reviewer runs the service from the README alone",
        "The CI script fails when the health probe fails",
      ],
      [
        "Happy path: compose up serves the endpoint",
        "Failure: a stopped container is reported by the probe",
      ],
      "The runbook, CI output, and the recorded recovery step.",
    ),
  ],
  source: "fallback",
  runnable_project_id: null,
};

/**
 * Fixture-mode briefs. They are labeled fallbacks and never claim a provider ran.
 * In live mode the same shape comes from GET /api/project-briefs.
 */
export function fixturePlans(sessionId: string, analysisId: string): ProjectBriefs {
  return {
    session_id: sessionId,
    analysis_id: analysisId,
    plans: [sqlPlan, reactPlan, dockerPlan, pythonPlan],
    source: "fallback",
    message:
      "Demo fixture briefs: no project writer ran. Connect the API and generate to tailor them to a posting.",
  };
}
