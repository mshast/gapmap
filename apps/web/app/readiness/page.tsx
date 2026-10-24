"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, BadgeCheck, CircleHelp, LoaderCircle, LockKeyhole } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { StatusPill } from "@/components/StatusPill";
import { useAppState } from "@/components/AppStateProvider";
import { getProject, getReadiness, isMockMode } from "@/lib/api";

export default function ReadinessPage() {
  const router = useRouter();
  const { state, setState, hydrated } = useAppState();
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
      const project = await getProject(analysis.recommended_project_id);
      setState((current) => ({ ...current, project }));
      router.push(`/project/${project.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Project could not be loaded. Try again.");
    } finally {
      setLoadingProject(false);
    }
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

        {assessable && analysis.recommended_project_id && (
          <section className="project-callout">
            <div className="callout-index">NEXT<br />MOVE</div>
            <div className="callout-content"><p className="eyebrow">A JOB-RELEVANT WORK SAMPLE</p><h2>Investigate an E-commerce Revenue Bug</h2><p>Trace a revenue mismatch with three SQL tasks. Your draft stays in this browser session.</p></div>
            <button className="button button-primary" type="button" onClick={startProject} disabled={loadingProject}>{loadingProject ? <><LoaderCircle className="spin" size={16} /> Opening</> : <>Start project <ArrowRight size={17} /></>}</button>
          </section>
        )}
        {error && <div className="form-error" role="alert">{error}</div>}
        {isMockMode && <p className="fixture-note">Demo mode: these requirements are fixture-backed, not generated for arbitrary postings.</p>}
      </section>
    </AppShell>
  );
}