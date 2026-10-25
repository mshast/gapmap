import type { Requirement } from "@/lib/types";

export type ProjectPlan = {
  id: string;
  title: string;
  skills: string[];
  why: string;
  deliverable: string;
  steps: string[];
  runnableProjectId?: string;
};

const sqlSkills = new Set(["sql_joins", "sql_filtering", "sql_aggregation", "sql_refund_edge_cases"]);

export const skillLabels: Record<string, string> = {
  sql_joins: "SQL joins",
  sql_filtering: "SQL filtering",
  sql_aggregation: "SQL aggregation",
  sql_refund_edge_cases: "Refund edge cases",
  python: "Python",
  react: "React",
  docker: "Docker",
  dsa: "Data structures",
  java: "Java",
  cpp: "C++",
  csharp: "C#",
  javascript: "JavaScript",
  typescript: "TypeScript",
  cloud: "Cloud",
  git: "Git",
  apis: "APIs",
  testing: "Testing",
  machine_learning: "Machine learning",
  linux: "Linux",
  eligibility: "Eligibility",
};

export const skillLabel = (skill: string) => skillLabels[skill] ?? skill.replace(/_/g, " ");

export function isEligibility(requirement: Requirement) {
  // Older saved sessions predate the eligibility tag, so keep the wording check.
  return requirement.skill_ids.includes("eligibility")
    || (requirement.skill_ids.every((skill) => skill === "other")
      && /graduat|degree|bachelor|work authorization|authorized to work|citizen|visa|sponsor/i.test(requirement.job_quote));
}

const specs: Record<string, Pick<ProjectPlan, "title" | "deliverable" | "steps">> = {
  python: {
    title: "Build a Python workflow",
    deliverable: "A tested Python tool with documented inputs, outputs, and failure cases.",
    steps: ["Choose one real workflow from the role", "Implement the core path and validation", "Add tests and a short usage guide"],
  },
  react: {
    title: "Ship a React workflow",
    deliverable: "A responsive React feature with loading, error, empty, and success states.",
    steps: ["Turn the requirement into one user task", "Build accessible interactions", "Add responsive and interaction tests"],
  },
  docker: {
    title: "Containerize a production-shaped service",
    deliverable: "A minimal container with a health check and one-command startup.",
    steps: ["Create a small production image", "Add runtime health and configuration", "Document build, run, and recovery"],
  },
  dsa: {
    title: "Build an algorithm case study",
    deliverable: "A benchmarked implementation that explains the data structure and complexity tradeoffs.",
    steps: ["Define representative inputs and constraints", "Implement and test two approaches", "Compare complexity and measured performance"],
  },
  java: {
    title: "Build a Java REST service",
    deliverable: "A small Java service with typed models, input validation, and JUnit tests.",
    steps: ["Model one resource the team would own", "Implement create, read, and list endpoints", "Cover success and failure paths with JUnit"],
  },
  cpp: {
    title: "Write a performance-minded C++ tool",
    deliverable: "A CMake-built C++ program with unit tests and a short benchmark write-up.",
    steps: ["Pick a parsing or data-processing task", "Implement it with clear memory ownership", "Add tests and benchmark one optimization"],
  },
  csharp: {
    title: "Build a C# / .NET API",
    deliverable: "An ASP.NET Core API with validation, structured errors, and xUnit tests.",
    steps: ["Define one domain model and its rules", "Expose it through a minimal API", "Test the endpoints and document setup"],
  },
  javascript: {
    title: "Build a JavaScript feature end to end",
    deliverable: "A Node.js or browser feature with async error handling and automated tests.",
    steps: ["Pick one user-facing task from the role", "Implement it with clean async data flow", "Add tests for success, empty, and error cases"],
  },
  typescript: {
    title: "Ship a strictly typed TypeScript module",
    deliverable: "A TypeScript library or API client with strict types, runtime validation, and tests.",
    steps: ["Define the types for one real data shape", "Validate untrusted input at the boundary", "Publish usage examples and tests"],
  },
  cloud: {
    title: "Deploy a service to the cloud",
    deliverable: "A small service running on AWS, GCP, or Azure with config, logs, and a teardown guide.",
    steps: ["Containerize or package a small API", "Deploy it with least-privilege credentials", "Add logging, a health check, and cleanup steps"],
  },
  git: {
    title: "Run a project through a team Git workflow",
    deliverable: "A repository with feature branches, reviewed pull requests, and a CI check.",
    steps: ["Split one feature into small branches", "Open pull requests with clear descriptions", "Add a CI check that blocks failing merges"],
  },
  apis: {
    title: "Design and ship a REST API",
    deliverable: "A documented REST API with validation, consistent error responses, and endpoint tests.",
    steps: ["Write the endpoint contract first", "Implement validation and error handling", "Test every endpoint and publish the docs"],
  },
  testing: {
    title: "Add a real test suite to a project",
    deliverable: "Unit and integration tests running in CI, plus a write-up of a bug they caught.",
    steps: ["Pick an untested project you already have", "Cover core logic and one integration path", "Run the suite in CI and fix what it finds"],
  },
  machine_learning: {
    title: "Train and evaluate a small ML model",
    deliverable: "A reproducible notebook or script with a baseline, evaluation metrics, and error analysis.",
    steps: ["Choose a small public dataset tied to the role", "Compare a baseline against one model", "Report metrics and where the model fails"],
  },
  linux: {
    title: "Automate a task on Linux",
    deliverable: "A shell script or CLI tool that automates a real workflow, with usage docs.",
    steps: ["Pick a repetitive developer task", "Script it with safe error handling", "Document usage and test it on a clean machine"],
  },
  other: {
    title: "Create a focused proof of work",
    deliverable: "A reviewable artifact with a clear problem, implementation, and evidence of the result.",
    steps: ["Translate the requirement into a concrete scenario", "Build the smallest useful artifact", "Document decisions, tests, and outcome"],
  },
};

const gapFactor = (requirement: Requirement) => (requirement.evidence_status === "unverified" ? 2 : 1);

function plansFor(requirement: Requirement): ProjectPlan[] {
  if (isEligibility(requirement)) return [];
  const plans: ProjectPlan[] = [];
  const sql = requirement.skill_ids.filter((skill) => sqlSkills.has(skill));
  if (sql.length) {
    plans.push({
      id: "revenue-debug-001",
      title: "Investigate an E-commerce Revenue Bug",
      skills: sql,
      why: `Targets the role's ${requirement.label.toLowerCase()} requirement with a graded SQL investigation.`,
      deliverable: "A tested SQL report with correct gross and net revenue by region.",
      steps: ["Join completed orders to customer regions", "Recalculate gross revenue", "Correct net revenue after multiple refunds"],
      runnableProjectId: "revenue-debug-001",
    });
  }
  // One plan per named skill, shared across requirements that ask for it.
  const named = requirement.skill_ids.filter((skill) => !sqlSkills.has(skill) && skill !== "other" && specs[skill]);
  for (const skill of named) {
    plans.push({
      id: `gap-${skill}`,
      ...specs[skill],
      skills: [skill],
      why: `Builds direct evidence for “${requirement.job_quote}”`,
    });
  }
  if (!plans.length) {
    plans.push({
      id: `gap-${requirement.id}`,
      ...specs.other,
      title: `${specs.other.title}: ${requirement.label}`,
      skills: [requirement.label],
      why: `Builds direct evidence for “${requirement.job_quote}”`,
    });
  }
  return plans;
}

export function plansForRequirements(requirements: Requirement[], excludeDemonstrated = true) {
  const seen = new Set<string>();
  // Biggest gaps first, mirroring the roadmap priority; the sort is stable on ties.
  return requirements
    .filter((requirement) => !excludeDemonstrated || requirement.evidence_status !== "demonstrated_on_project")
    .sort((a, b) => b.importance * gapFactor(b) - a.importance * gapFactor(a))
    .flatMap(plansFor)
    .filter((plan) => {
      if (seen.has(plan.id)) return false;
      seen.add(plan.id);
      return true;
    })
    .sort((a, b) => Number(Boolean(b.runnableProjectId)) - Number(Boolean(a.runnableProjectId)));
}
