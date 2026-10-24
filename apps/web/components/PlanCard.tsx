import type { ReactNode } from "react";
import { planSkills } from "@/lib/projectPlans";
import type { ProjectPlan } from "@/lib/types";

const sourceLabels: Record<ProjectPlan["source"], string> = {
  graded: "Graded project",
  template: "Project plan",
  ai_suggested: "AI-suggested idea",
};

export function PlanCard({ plan, action }: { plan: ProjectPlan; action?: ReactNode }) {
  return (
    <article className={`plan-card${plan.runnable_project_id ? " plan-card-primary" : ""}`}>
      <div>
        <span className="plan-label">{sourceLabels[plan.source]} · {planSkills(plan)}</span>
        <h3>{plan.title}</h3>
        <p>{plan.why}</p>
        <p className="plan-deliverable"><b>You&apos;ll leave with:</b> {plan.deliverable}</p>
        <ol>{plan.steps.map((step) => <li key={step}>{step}</li>)}</ol>
        {plan.source === "ai_suggested" && <p className="plan-note">Suggested by AI for this posting. Not reviewed or graded by GapMap.</p>}
      </div>
      {action}
    </article>
  );
}
