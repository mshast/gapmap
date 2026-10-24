import type {
  Analysis,
  Project,
  Readiness,
  RunResult,
  Submission,
} from "@/lib/types";

export const isMockMode = process.env.NEXT_PUBLIC_GAPMAP_MOCK !== "false";

const demoResume = `Maya Chen
Computer Science student

Projects
- Built a Python service that validates campus event data and produces weekly reports.
- Collaborated with three classmates to test and document the service.

Skills
- Python, Git, testing, technical writing`;

const demoJob = `Software Engineering Intern

Join our team to build and improve reliable customer-facing software.
Experience with SQL databases is required.
Experience with Python is required.
Experience building user interfaces with React is preferred.
Familiarity with Docker containers is preferred.
Strong collaborative problem-solving skills are preferred.`;

const demoProject: Project = {
  id: "revenue-debug-001",
  title: "Investigate an E-commerce Revenue Bug",
  scenario:
    "The weekly revenue dashboard does not match finance. Trace the issue and build a trustworthy net revenue report.",
  schema_text:
    "customers(id, name, region)\norders(id, customer_id, amount_cents, status, created_at)\nrefunds(id, order_id, amount_cents)",
  competencies: ["sql_joins", "sql_filtering", "sql_aggregation", "refund_edge_cases"],
  tasks: [
    {
      id: "t1",
      title: "Connect orders to customer regions",
      instructions: "List completed orders with each customer region. Return order id, region, and amount_cents.",
      expected_columns: ["order_id", "region", "amount_cents"],
      starter_sql: `SELECT
  o.id AS order_id,
  c.region,
  o.amount_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed';`,
    },
    {
      id: "t2",
      title: "Find gross revenue by region",
      instructions: "Aggregate completed order revenue by region. Ignore pending and cancelled orders.",
      expected_columns: ["region", "gross_revenue_cents"],
      starter_sql: `SELECT
  c.region,
  SUM(o.amount_cents) AS gross_revenue_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.region;`,
    },
    {
      id: "t3",
      title: "Account for refunds",
      instructions: "Calculate net revenue by region. Multiple refunds must not duplicate order revenue; orders without refunds still count.",
      expected_columns: ["region", "net_revenue_cents"],
      starter_sql: `-- Aggregate refunds per order before joining to completed orders.
WITH refund_totals AS (
  SELECT order_id, SUM(amount_cents) AS refund_cents
  FROM refunds
  GROUP BY order_id
)
SELECT
  c.region,
  SUM(o.amount_cents - COALESCE(r.refund_cents, 0)) AS net_revenue_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
LEFT JOIN refund_totals r ON r.order_id = o.id
WHERE o.status = 'completed'
GROUP BY c.region;`,
    },
  ],
};

function errorMessage(body: unknown, fallback: string): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(body, "The request could not be completed. Try again."));
  return body as T;
}

const mockRequirements = (resume: string) => {
  const pythonQuote = resume.match(/- Built a Python[^\n]*/)?.[0]?.replace(/^- /, "");
  const teamworkQuote = resume.match(/- Collaborated[^\n]*/)?.[0]?.replace(/^- /, "");
  return [
    {
      id: "req-sql",
      label: "SQL relational querying",
      job_quote: "Experience with SQL databases is required.",
      importance: 3,
      requirement_type: "required" as const,
      skill_ids: ["sql_joins", "sql_filtering", "sql_aggregation"],
      resume_quotes: [],
      evidence_status: "unverified" as const,
      verification_capability: "available" as const,
      uncovered_skill_ids: [],
    },
    {
      id: "req-python",
      label: "Python programming",
      job_quote: "Experience with Python is required.",
      importance: 3,
      requirement_type: "required" as const,
      skill_ids: ["python"],
      resume_quotes: pythonQuote ? [pythonQuote] : [],
      evidence_status: pythonQuote ? ("resume_evidence" as const) : ("unverified" as const),
      verification_capability: "not_assessable" as const,
      uncovered_skill_ids: ["python"],
    },
    {
      id: "req-react",
      label: "React interfaces",
      job_quote: "Experience building user interfaces with React is preferred.",
      importance: 2,
      requirement_type: "preferred" as const,
      skill_ids: ["react"],
      resume_quotes: [],
      evidence_status: "unverified" as const,
      verification_capability: "not_assessable" as const,
      uncovered_skill_ids: ["react"],
    },
    {
      id: "req-docker",
      label: "Docker containers",
      job_quote: "Familiarity with Docker containers is preferred.",
      importance: 2,
      requirement_type: "preferred" as const,
      skill_ids: ["docker"],
      resume_quotes: [],
      evidence_status: "unverified" as const,
      verification_capability: "not_assessable" as const,
      uncovered_skill_ids: ["docker"],
    },
    {
      id: "req-collaboration",
      label: "Collaborative problem-solving",
      job_quote: "Strong collaborative problem-solving skills are preferred.",
      importance: 1,
      requirement_type: "preferred" as const,
      skill_ids: ["collaboration"],
      resume_quotes: teamworkQuote ? [teamworkQuote] : [],
      evidence_status: teamworkQuote ? ("resume_evidence" as const) : ("unverified" as const),
      verification_capability: "not_assessable" as const,
      uncovered_skill_ids: ["collaboration"],
    },
  ];
};

export async function getDemoFixture(): Promise<{ resume_text: string; job_description: string }> {
  if (isMockMode) return { resume_text: demoResume, job_description: demoJob };
  return request("/api/demo/fixture");
}

export async function analyze(resumeText: string, jobDescription: string): Promise<Analysis> {
  if (isMockMode) {
    return {
      session_id: crypto.randomUUID(),
      analysis_id: crypto.randomUUID(),
      target_role: "Software Engineering Intern",
      recommended_project_id: demoProject.id,
      requirements: mockRequirements(resumeText),
      roadmap: [
        { requirement_id: "req-sql", action: "Complete the revenue debugging project", priority: 1 },
        { requirement_id: "req-python", action: "Keep a concise example of your Python service ready to discuss", priority: 2 },
        { requirement_id: "req-react", action: "Build a small React interface to add a concrete example", priority: 3 },
      ],
    };
  }
  return request("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_text: resumeText, job_description: jobDescription }),
  });
}

export async function getProject(projectId: string): Promise<Project> {
  if (isMockMode) return demoProject;
  return request(`/api/projects/${encodeURIComponent(projectId)}`);
}

export async function runQuery(
  projectId: string,
  sessionId: string,
  taskId: string,
  sql: string,
): Promise<RunResult> {
  if (isMockMode) {
    if (!sql.trim()) return { columns: [], rows: [], truncated: false, error: "Add a query before running the preview." };
    const taskIndex = demoProject.tasks.findIndex((task) => task.id === taskId);
    const rows = [
      [[101, "West", 129900], [102, "Northeast", 104500], [103, "South", 81900]],
      [["West", 129900], ["Northeast", 104500], ["South", 81900]],
      [["West", 124500], ["Northeast", 98200], ["South", 76100]],
    ][Math.max(taskIndex, 0)];
    return {
      columns: demoProject.tasks[Math.max(taskIndex, 0)].expected_columns,
      rows,
      truncated: false,
      error: null,
    };
  }
  return request(`/api/projects/${encodeURIComponent(projectId)}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, task_id: taskId, sql }),
  });
}

export async function submitTask(
  projectId: string,
  sessionId: string,
  taskId: string,
  sql: string,
): Promise<Submission> {
  if (isMockMode) {
    const taskIndex = demoProject.tasks.findIndex((task) => task.id === taskId);
    const taskScores = [
      { earned: 25, possible: 25 },
      { earned: 16, possible: 20 },
      { earned: 0, possible: 55 },
    ];
    const score = taskScores[Math.max(taskIndex, 0)];
    const competencyScores = [
      [{ earned: 25, possible: 25, skill_id: "sql_joins", status: "demonstrated_on_project" as const }],
      [
        { earned: 12, possible: 20, skill_id: "sql_filtering", status: "partially_demonstrated" as const },
        { earned: 4, possible: 25, skill_id: "sql_aggregation", status: "partially_demonstrated" as const },
      ],
      [{ earned: 0, possible: 30, skill_id: "refund_edge_cases", status: "unverified" as const }],
    ][Math.max(taskIndex, 0)];
    return {
      submission_id: crypto.randomUUID(),
      task_id: taskId,
      task_score: score,
      competency_scores: competencyScores,
      public_test_feedback: [
        {
          label: taskIndex === 2 ? "Multiple refunds per order" : "Visible sample cases",
          passed: taskIndex < 2,
          explanation: taskIndex < 2 ? "The fixture response shows the expected sample output." : "The mock fixture does not assess this task.",
        },
      ],
    };
  }
  return request(`/api/projects/${encodeURIComponent(projectId)}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, task_id: taskId, sql }),
  });
}

export async function getReadiness(sessionId: string): Promise<Readiness> {
  if (isMockMode) throw new Error("Mock readiness is derived from the saved demo session.");
  return request(`/api/readiness?session_id=${encodeURIComponent(sessionId)}`);
}