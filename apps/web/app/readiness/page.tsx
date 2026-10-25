"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, BadgeCheck, CircleHelp, LoaderCircle, LockKeyhole, Sparkles, TriangleAlert } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { PlanCard } from "@/components/PlanCard";
import { StatusPill } from "@/components/StatusPill";
import { useAppState } from "@/components/AppStateProvider";
import {
  generateProjectBriefs,
  getProject,
  getProjectBriefs,
  getReadiness,
  isMockMode,
} from "@/lib/api";
import { isEligibility, plansForRequirements, skillLabel } from "@/lib/projectPlans";
import { cleanQuote } from "@/lib/text";
import { SessionExpiredNotice, isSessionExpired } from "@/components/SessionExpiredNotice";
import type { ProjectBrief } from "@/lib/types";

const sourceLabel = (source: ProjectBrief["source"]) =>
  source === "generated" ? "Tailored from this posting" : "Fallback project template";

export default function ReadinessPage() {
  const { state, setState, hydrated } = useAppState();
  const router = useRouter();
  const [error, setError] = useState("");
  const [planError, setPlanError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [starting, setStarting] = useState(false);
  const [filter, setFilter] = useState<"all" | "gaps" | "assessable" | "required">("all");
  const analysis = state.analysis;
  const sessionId = analysis?.session_id;
  const analysisId = analysis?.analysis_id;
  const readiness = state.readiness?.session_id === sessionId ? state.readiness : null;
  const requirements = readiness?.requirements ?? analysis?.requirements ?? [];
  const evidencedCount = requirements.filter((item) => item.evidence_status !== "unverified").length;
  const testedCount = requirements.filter((item) => item.evidence_status === "partially_demonstrated" || item.evidence_status === "demonstrated_on_project").length;
  const unverifiedCount = requirements.filter((item) => item.evidence_status === "unverified").length;
  const assessableCount = requirements.filter((item) => item.verification_capability === "available").length;
  const requiredCount = requirements.filter((item) => item.requirement_type === "required").length;

  const filteredRequirements = requirements.filter((item) => {
    if (filter === "gaps") return item.evidence_status === "unverified";
    if (filter === "assessable") return item.verification_capability === "available";
    if (filter === "required") return item.requirement_type === "required";
    return true;
  });

  const briefs = state.plans?.analysis_id === analysisId ? state.plans : null;
  const briefPlans = briefs?.plans ?? [];
  const skillPlans = plansForRequirements(requirements);
  // Loading is derived, so the effect below never sets state synchronously.
  const loadingPlans = Boolean(sessionId) && !briefs && !planError;

  useEffect(() => {
    if (!hydrated || !sessionId || !analysisId) return;
    if (state.plans?.analysis_id === analysisId || planError) return;
    let active = true;
    getProjectBriefs(sessionId, analysisId)
      .then((result) => { if (active) setState((current) => ({ ...current, plans: result })); })
      .catch((caught: unknown) => { if (active) setPlanError(caught instanceof Error ? caught.message : "Project briefs could not be loaded."); });
    return () => { active = false; };
  }, [hydrated, sessionId, analysisId, state.plans?.analysis_id, planError, setState]);

  useEffect(() => {
    if (!hydrated || isMockMode || !analysis?.session_id) return;
    let active = true;
    getReadiness(analysis.session_id)
      .then((latest) => { if (active) setState((current) => ({ ...current, readiness: latest })); })
      .catch((caught: unknown) => { if (active) setError(caught instanceof Error ? caught.message : "Readiness could not be refreshed."); });
    return () => { active = false; };
  }, [analysis?.session_id, hydrated, setState]);

  async function generate() {
    if (!analysis?.session_id) return;
    setGenerating(true);
    setPlanError("");
    try {
      const result = await generateProjectBriefs(analysis.session_id, analysis.analysis_id);
      setState((current) => ({ ...current, plans: result }));
    } catch (caught) {
      setPlanError(caught instanceof Error ? caught.message : "Tailored briefs could not be generated.");
    } finally {
      setGenerating(false);
    }
  }

  async function openProject(projectId: string) {
    setStarting(true);
    setError("");
    try {
      const project = await getProject(projectId);
      setState((current) => ({ ...current, project }));
      router.push(`/project/${project.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The graded assessment could not be loaded.");
      setStarting(false);
    }
  }

  async function startProject(plan: ProjectBrief) {
    if (plan.runnable_project_id) await openProject(plan.runnable_project_id);
  }

  if (!hydrated) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading saved session…</div></AppShell>;
  if (!analysis) return <AppShell><div className="page-wrap empty-state"><p className="eyebrow">NO ANALYSIS YET</p><h1>Start with a role.</h1><p>Add a resume and posting to see traceable requirements.</p><Link className="button button-primary" href="/">Go to input <ArrowRight size={16} /></Link></div></AppShell>;

  return (
    <AppShell>
      <section className="page-wrap readiness-page">
        <div className="section-topline">
          <p className="eyebrow"><span className="eyebrow-line" /> YOUR EVIDENCE MAP / 02</p>
          <span className="role-chip">{analysis.target_role}</span>
        </div>
        <div className="readiness-heading">
          <div>
            <h1>What the role asks.<br /><em>What you can show.</em></h1>
            <p className="intro-copy">A resume mention is a claim. A project result is tested evidence. GapMap keeps those separate.</p>
          </div>
          <div className="evidence-counter">
            <span className="counter-value">{evidencedCount}<span> / {requirements.length}</span></span>
            <span className="counter-label">{testedCount ? `requirements with evidence · ${testedCount} tested on project` : "requirements with resume evidence"}</span>
          </div>
        </div>

        {isSessionExpired(error) && <SessionExpiredNotice />}

        {analysis.analysis_mode === "demo" && (
          <div className="mock-banner" role="status">
            <TriangleAlert size={16} />
            <span><b>Demo fixture.</b> {analysis.warnings?.join(" ")}</span>
          </div>
        )}

        <div className="filter-bar" role="tablist" aria-label="Filter requirements">
          <button type="button" className={`filter-chip${filter === "all" ? " active" : ""}`} onClick={() => setFilter("all")}>
            All ({requirements.length})
          </button>
          <button type="button" className={`filter-chip${filter === "gaps" ? " active" : ""}`} onClick={() => setFilter("gaps")}>
            Gaps to build ({unverifiedCount})
          </button>
          <button type="button" className={`filter-chip${filter === "assessable" ? " active" : ""}`} onClick={() => setFilter("assessable")}>
            Covered by assessment ({assessableCount})
          </button>
          <button type="button" className={`filter-chip${filter === "required" ? " active" : ""}`} onClick={() => setFilter("required")}>
            Required only ({requiredCount})
          </button>
        </div>

        <div className="requirement-list" aria-label="Job requirements">
          {filteredRequirements.length === 0 && (
            <div className="empty-result" style={{ padding: "24px 0", textAlign: "center" }}>
              No requirements match this filter.
            </div>
          )}
          {filteredRequirements.map((requirement, index) => (
            <article className="requirement-row" key={requirement.id}>
              <span className="requirement-index">0{index + 1}</span>
              <div className="requirement-main">
                <div className="requirement-title-line">
                  <h2>{requirement.label}</h2>
                  <span className={`importance importance-${requirement.requirement_type}`}>{requirement.requirement_type}</span>
                </div>
                <blockquote>{requirement.job_quote}</blockquote>
                {(requirement.resume_quotes ?? []).length > 0 ? (
                  <div className="evidence-quote"><BadgeCheck size={15} /><span><b>Resume claim</b> “{cleanQuote(requirement.resume_quotes?.[0] ?? "")}”</span></div>
                ) : (
                  <div className="evidence-absent"><CircleHelp size={15} /><span>{isEligibility(requirement) ? "Not stated on your resume. Add it if it applies to you." : "No resume evidence found. That is a gap to investigate, not a verdict."}</span></div>
                )}
              </div>
              <div className="requirement-status">
                <StatusPill status={requirement.evidence_status} />
                {isEligibility(requirement) ? <span className="not-covered">Eligibility, not a skill</span> : requirement.verification_capability === "not_assessable" ? <span className="not-covered"><LockKeyhole size={13} /> No matching test yet</span> : <span className="can-test">Covered by the SQL assessment</span>}
              </div>
            </article>
          ))}
        </div>

        <section className="recommendation-section" aria-labelledby="project-plans-title">
          <div className="section-heading">
            <div><p className="stage-kicker">PROJECT PLANS</p><h2 id="project-plans-title">Starting points for each gap.</h2></div>
            <span className="section-note">Highest-priority gaps first</span>
          </div>
          {skillPlans.length === 0 ? <div className="empty-result">No skill gaps to build a project for. Every requirement already has evidence or is an eligibility condition.</div> : <div className="plan-grid">{skillPlans.slice(0, 4).map((plan) => <PlanCard key={plan.id} plan={plan} action={plan.runnable_project_id && <button className="button button-primary" type="button" onClick={() => void openProject(plan.runnable_project_id!)} disabled={starting}>{starting ? <><LoaderCircle className="spin" size={15} /> Opening</> : <>Start graded assessment <ArrowRight size={15} /></>}</button>} />)}</div>}
          {skillPlans.length > 4 && <p className="field-meta">Showing the 4 highest-priority plans of {skillPlans.length}. The full list is on the results page.</p>}
        </section>

        <section className="recommendation-section" aria-labelledby="assessment-title">
          <div className="section-heading">
            <div><p className="stage-kicker">DETAILED PROJECT BRIEFS</p><h2 id="assessment-title">Milestone-level plans for your specific gaps.</h2></div>
            <div className="plan-actions">
              {!isMockMode && briefs?.source !== "generated" && <button className="button button-outline button-small" type="button" onClick={generate} disabled={generating || loadingPlans}>{generating ? <><LoaderCircle className="spin" size={14} /> Writing briefs</> : <><Sparkles size={14} /> Generate tailored projects</>}</button>}
              {briefs?.source === "generated" && <span className="section-note">Tailored briefs are saved for this analysis.</span>}
            </div>
          </div>
          {briefs?.message && <p className="plan-status" role="status">{briefs.message}</p>}
          {planError && <div className="form-error" role="alert">{planError} <button className="text-button" type="button" onClick={() => setPlanError("")}>Retry</button></div>}
          {loadingPlans && briefPlans.length === 0 ? <div className="plan-grid" aria-busy="true">{[0, 1].map((index) => <div className="plan-card plan-skeleton" key={index}><span /><span /><span /></div>)}</div> : briefPlans.length > 0 ? <div className="plan-grid">{briefPlans.map((plan) => <article className={`plan-card${plan.runnable_project_id ? " plan-card-primary" : ""}`} key={plan.id}><div><span className="plan-label">{sourceLabel(plan.source)} · {plan.skills.map(skillLabel).join(" · ")}</span><h3>{plan.title}</h3><p>{plan.summary}</p><p className="plan-deliverable"><b>You&apos;ll leave with:</b> {plan.deliverables[0]}</p><p className="plan-meta">{plan.milestones.length} milestones · {plan.milestones.reduce((count, item) => count + item.tests.length, 0)} tests</p></div><div className="plan-card-actions">{plan.runnable_project_id && <button className="button button-primary" type="button" onClick={() => void startProject(plan)} disabled={starting}>{starting ? <><LoaderCircle className="spin" size={15} /> Opening</> : <>Start revenue debugging project <ArrowRight size={15} /></>}</button>}<Link className="button button-outline" href={`/projects/${plan.id}`}>View project brief <ArrowRight size={15} /></Link></div></article>)}</div> : <div className="empty-result">No project-eligible gaps remain for this analysis. Keep the graded result as evidence and add another posting when the target role changes.</div>}
        </section>

        <section className="project-callout">
          <span className="callout-index">05 /<br />PRACTICE</span>
          <div className="callout-content"><p className="eyebrow">MOCK INTERVIEW</p><h2>Practice talking about this role.</h2><p>Five questions from your resume and this posting, with rubric feedback on each answer.</p></div>
          <Link className="button button-outline" href="/interview">Practice interview <ArrowRight size={16} /></Link>
        </section>
        {error && !isSessionExpired(error) && <div className="form-error" role="alert">{error}</div>}
        {isMockMode && <p className="fixture-note">Demo mode uses the labeled example role. Generate tailored projects once the API is connected.</p>}
      </section>
    </AppShell>
  );
}
