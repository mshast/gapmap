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
  other: {
    title: "Create a focused proof of work",
    deliverable: "A reviewable artifact with a clear problem, implementation, and evidence of the result.",
    steps: ["Translate the requirement into a concrete scenario", "Build the smallest useful artifact", "Document decisions, tests, and outcome"],
  },
};

function planFor(requirement: Requirement): ProjectPlan | null {
  const skills = requirement.uncovered_skill_ids?.length
    ? requirement.uncovered_skill_ids
    : requirement.skill_ids;
  if (skills.some((skill) => sqlSkills.has(skill))) {
    return {
      id: `gap-${requirement.id}`,
      title: "Investigate an E-commerce Revenue Bug",
      skills: skills.filter((skill) => sqlSkills.has(skill)),
      why: `Targets the role's ${requirement.label.toLowerCase()} requirement with a graded SQL investigation.`,
      deliverable: "A tested SQL report with correct gross and net revenue by region.",
      steps: ["Join completed orders to customer regions", "Recalculate gross revenue", "Correct net revenue after multiple refunds"],
      runnableProjectId: "revenue-debug-001",
    };
  }

  const skill = skills.find((item) => specs[item]) ?? "other";
  const spec = specs[skill];
  const eligibility = /graduat|degree|work authorization|citizen|visa|sponsor/i.test(requirement.job_quote);
  if (eligibility) return null;
  return {
    id: `gap-${requirement.id}`,
    title: `${spec.title}: ${requirement.label}`,
    skills,
    why: `Builds direct evidence for “${requirement.job_quote}”`,
    deliverable: spec.deliverable,
    steps: spec.steps,
  };
}

export function plansForRequirements(requirements: Requirement[], excludeDemonstrated = true) {
  const seen = new Set<string>();
  return requirements
    .filter((requirement) => !excludeDemonstrated || requirement.evidence_status !== "demonstrated_on_project")
    .map(planFor)
    .filter((plan): plan is ProjectPlan => {
      if (!plan || seen.has(plan.id)) return false;
      seen.add(plan.id);
      return true;
    });
}

export function findPlan(requirements: Requirement[], planId: string) {
  return plansForRequirements(requirements, false).find((plan) => plan.id === planId);
}
