"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, BadgeCheck, CircleHelp, LoaderCircle, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { StatusPill } from "@/components/StatusPill";
import { useAppState } from "@/components/AppStateProvider";
import { getProject, getReadiness, isMockMode } from "@/lib/api";

export default function ReadinessPage() {
  const { state, setState, hydrated } = useAppState();
  const router = useRouter();
  const [loadingProject, setLoadingProject] = useState(false);
  const [error, setError] = useState("");
  const analysis = state.analysis;
  // Prefer server readiness: it includes graded project results for this session.
  const readiness = state.readiness?.session_id === analysis?.session_id ? state.readiness : null;
  const requirements = readiness?.requirements ?? analysis?.requirements ?? [];
  const evidencedCount = requirements.filter((item) => item.evidence_status !== "unverified").length;
  const testedCount = requirements.filter((item) => item.evidence_status === "partially_demonstrated" || item.evidence_status === "demonstrated_on_project").length;
  const assessable = requirements.some((item) => item.verification_capability === "available");

  useEffect(() => {
    if (!hydrated || isMockMode || !analysis?.session_id) return;
    let active = true;
    getReadiness(analysis.session_id)
      .then((latest) => { if (active) setState((current) => ({ ...current, readiness: latest })); })
      .catch((caught: unknown) => { if (active) setError(caught instanceof Error ? caught.message : "Readiness could not be refreshed."); });
    return () => { active = false; };
  }, [analysis?.session_id, hydrated, setState]);

  async function startProject() {
    if (!analysis?.recommended_project_id) return;
    setError("");
    setLoadingProject(true);
    try {
      const project = await getProject(projectId);
      setState((current) => ({ ...current, project }));
      router.push(`/project/${project.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Project could not be loaded. Try again.");
    } finally { setLoadingProject(false); }
  }

  if (!hydrated) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading saved session…</div></AppShell>;
  if (!analysis) return <AppShell><div className="page-wrap empty-state"><p className="eyebrow">NO ANALYSIS YET</p><h1>Start with a role.</h1><p>Add a resume and posting to see traceable requirements.</p><Link className="button button-primary" href="/">Go to input <ArrowRight size={16} /></Link></div></AppShell>;

  return (
    <AppShell>
      <section className="page-wrap readiness-page">
        <div className="section-topline"><p className="eyebrow"><span className="eyebrow-line" /> YOUR EVIDENCE MAP / 02</p><span className="role-chip">{analysis.target_role}</span></div>
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

        <div className="requirement-list" aria-label="Job requirements">
          {requirements.map((requirement, index) => (
            <article className="requirement-row" key={requirement.id}>
              <span className="requirement-index">0{index + 1}</span>
              <div className="requirement-main">
                <div className="requirement-title-line">
                  <h2>{requirement.label}</h2>
                  <span className={`importance importance-${requirement.requirement_type}`}>{requirement.requirement_type}</span>
                </div>
                <blockquote>{requirement.job_quote}</blockquote>
                {(requirement.resume_quotes ?? []).length > 0 ? (
                  <div className="evidence-quote"><BadgeCheck size={15} /><span><b>Resume claim</b> “{requirement.resume_quotes?.[0]}”</span></div>
                ) : (
                  <div className="evidence-absent"><CircleHelp size={15} /><span>No supporting resume quote found. That does not mean you lack the skill.</span></div>
                )}
              </div>
              <div className="requirement-status">
                <StatusPill status={requirement.evidence_status} />
                {requirement.verification_capability === "not_assessable" && <span className="not-covered"><LockKeyhole size={13} /> No verification project available</span>}
                {requirement.verification_capability === "available" && <span className="can-test">Project can test this</span>}
              </div>
            </article>
          ))}
        </div>

  return <AppShell><section className="page-wrap readiness-page">
    <div className="stage-header"><div><p className="stage-kicker">STEP 2 OF 3 · EVIDENCE MAP</p><h1>What this role asks — and what you can prove.</h1><p className="intro-copy">We found {requirements.length} requirements for <strong>{analysis.target_role}</strong>. Resume evidence is self-reported; project evidence is tested.</p></div><div className="evidence-counter"><strong>{evidencedCount}<span> / {requirements.length}</span></strong><small>with evidence so far</small></div></div>
    <div className="step-bar" aria-label="GapMap steps"><span className="done">1 Analyze</span><span className="current">2 Assess gaps</span><span>3 Choose next steps</span></div>
    <div className="requirement-list" aria-label="Job requirements">{requirements.map((requirement) => <article className="requirement-row" key={requirement.id}><div className="requirement-main"><div className="requirement-title-line"><h2>{requirement.label}</h2><span className={`importance importance-${requirement.requirement_type}`}>{requirement.requirement_type}</span></div><blockquote>{requirement.job_quote}</blockquote>{(requirement.resume_quotes ?? []).length > 0 ? <div className="evidence-quote"><BadgeCheck size={15} /><span><b>Resume claim</b> “{requirement.resume_quotes?.[0]}”</span></div> : <div className="evidence-absent"><CircleHelp size={15} /><span>No resume evidence found. That is a gap to investigate, not a verdict.</span></div>}</div><div className="requirement-status"><StatusPill status={requirement.evidence_status} />{requirement.verification_capability === "not_assessable" ? <span className="not-covered"><LockKeyhole size={13} /> No matching test yet</span> : <span className="can-test">Covered by the SQL assessment</span>}</div></article>)}</div>
    <section className="recommendation-section" aria-labelledby="assessment-title"><div className="section-heading"><div><p className="stage-kicker">PROJECT PLANS</p><h2 id="assessment-title">Projects matched to your specific gaps.</h2></div><span className="section-note">Start with the highest-priority gap</span></div><div className="plan-grid">{plans.slice(0, 4).map((plan) => <article className={`plan-card${plan.runnableProjectId ? " plan-card-primary" : ""}`} key={plan.id}><div><span className="plan-label">TARGETED SPEC · {plan.skills.join(" · ")}</span><h3>{plan.title}</h3><p>{plan.why}</p><p className="plan-deliverable"><b>You&apos;ll leave with:</b> {plan.deliverable}</p><ol>{plan.steps.map((step) => <li key={step}>{step}</li>)}</ol></div>{plan.runnableProjectId && <button className="button button-primary" type="button" onClick={() => openProject(plan.runnableProjectId!)} disabled={loadingProject}>{loadingProject ? <LoaderCircle className="spin" size={16} /> : <>Start graded assessment <ArrowRight size={16} /></>}</button>}</article>)}</div></section>
    {error && <div className="form-error" role="alert">{error}</div>}{isMockMode && <p className="fixture-note">Demo mode uses the labeled example role. Live mode generates this map from your posting.</p>}
  </section></AppShell>;
}
