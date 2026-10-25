import type { ProjectPlan, Requirement } from "@/lib/types";

// Mirrors SKILL_LABELS in gapmap/apps/api/services/analysis/plans.py.
const skillLabels: Record<string, string> = {
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

export const planSkills = (plan: ProjectPlan) =>
  plan.skill_ids.filter((skill) => skill !== "other").map(skillLabel).join(" · ");

// Plans with a self-checked practice exercise in the browser.
export const practiceHref = (plan: ProjectPlan) => (plan.skill_ids.includes("python") ? "/practice/python" : null);

export const isEligibility = (requirement: Requirement) => requirement.skill_ids.includes("eligibility");

const gapFactor = (requirement: Requirement) => (requirement.evidence_status === "unverified" ? 2 : 1);

export function plansForRequirements(requirements: Requirement[], excludeDemonstrated = true) {
  const seen = new Set<string>();
  // Biggest gaps first, mirroring the roadmap priority; the sort is stable on ties.
  return requirements
    .filter((requirement) => !excludeDemonstrated || requirement.evidence_status !== "demonstrated_on_project")
    .sort((a, b) => b.importance * gapFactor(b) - a.importance * gapFactor(a))
    .flatMap((requirement) => requirement.project_plans ?? [])
    .filter((plan) => {
      if (seen.has(plan.id)) return false;
      seen.add(plan.id);
      return true;
    })
    .sort((a, b) => Number(Boolean(b.runnable_project_id)) - Number(Boolean(a.runnable_project_id)));
}
