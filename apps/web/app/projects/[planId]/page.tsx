"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, LoaderCircle } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAppState } from "@/components/AppStateProvider";
import { getProject } from "@/lib/api";
import type { ProjectBrief } from "@/lib/types";

const sourceLabel = (source: ProjectBrief["source"]) =>
  source === "generated" ? "Tailored from this posting" : "Fallback project template";

export default function ProjectBriefPage({ params }: { params: Promise<{ planId: string }> }) {
  const { planId } = use(params);
  const { state, setState, hydrated } = useAppState();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const analysis = state.analysis;
  const briefs = state.plans?.analysis_id === analysis?.analysis_id ? state.plans : null;
  const plan = briefs?.plans?.find((item) => item.id === planId);

  async function startAssessment() {
    if (!plan?.runnable_project_id) return;
    setError("");
    setLoading(true);
    try {
      const project = await getProject(plan.runnable_project_id);
      setState((current) => ({ ...current, project }));
      router.push(`/project/${project.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The graded assessment could not be loaded.");
      setLoading(false);
    }
  }

  if (!hydrated) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading project brief…</div></AppShell>;
  if (!analysis) return <AppShell><div className="page-wrap empty-state"><p className="eyebrow">PROJECT BRIEF</p><h1>Start with a role.</h1><p>Project briefs are built from the gaps in a saved role analysis.</p><Link className="button button-primary" href="/">Go to input <ArrowRight size={16} /></Link></div></AppShell>;
  if (!plan) return <AppShell><div className="page-wrap empty-state"><p className="eyebrow">PROJECT BRIEF</p><h1>This brief is not loaded.</h1><p>{briefs ? "The analysis may have changed. Return to the evidence map to choose a current brief." : "Open the evidence map to load the project briefs for this analysis."}</p><Link className="button button-primary" href="/readiness">Back to evidence map <ArrowRight size={16} /></Link></div></AppShell>;

  return <AppShell><section className="page-wrap project-spec-page">
    <div className="project-backline"><Link className="back-link" href="/readiness"><ArrowLeft size={15} /> Evidence map</Link><span className="project-step">PROJECT BRIEF</span></div>
    <header className="project-spec-header">
      <p className="stage-kicker">TARGETED TO {analysis.target_role}</p>
      <h1>{plan.title}</h1>
      <p className="plan-source">{sourceLabel(plan.source)} · {plan.skills.join(" · ")}</p>
      <p className="intro-copy">{plan.summary}</p>
      <blockquote className="brief-quote">“{plan.job_quote}”</blockquote>
    </header>

    <div className="project-spec-grid">
      <section className="project-spec-block">
        <p className="eyebrow">SCENARIO</p>
        <h2>Who this is for</h2>
        <p>{plan.scenario}</p>
      </section>
      <section className="project-spec-block">
        <p className="eyebrow">INPUTS / OUTPUTS</p>
        <h2>What goes in, what comes out</h2>
        <div className="brief-columns">
          <div><h3>Inputs</h3><ul className="brief-list">{plan.inputs.map((item) => <li key={item}>{item}</li>)}</ul></div>
          <div><h3>Outputs</h3><ul className="brief-list">{plan.outputs.map((item) => <li key={item}>{item}</li>)}</ul></div>
        </div>
      </section>
      <section className="project-spec-block">
        <p className="eyebrow">CONSTRAINTS</p>
        <h2>Limits that make it testable</h2>
        <ul className="brief-list">{plan.constraints.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
      <section className="project-spec-block">
        <p className="eyebrow">DELIVERABLES</p>
        <h2>What you publish</h2>
        <ul className="brief-list">{plan.deliverables.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
    </div>

    <section className="brief-milestones" aria-labelledby="milestones-title">
      <div className="section-heading"><div><p className="stage-kicker">BUILD PLAN</p><h2 id="milestones-title">Milestones and completion checks</h2></div><span className="section-note">{plan.milestones.length} ordered milestones</span></div>
      <ol className="milestone-list">
        {plan.milestones.map((milestone, index) => <li className="milestone" key={`${milestone.title}-${index}`}>
          <span className="milestone-index">0{index + 1}</span>
          <div>
            <h3>{milestone.title}</h3>
            <div className="milestone-grid">
              <div><h4>Work</h4><ul className="brief-list">{milestone.work.map((item) => <li key={item}>{item}</li>)}</ul></div>
              <div><h4>Done when</h4><ul className="brief-list">{milestone.acceptance_criteria.map((item) => <li key={item}>{item}</li>)}</ul></div>
              <div><h4>Tests</h4><ul className="brief-list">{milestone.tests.map((item) => <li key={item}>{item}</li>)}</ul></div>
            </div>
            <p className="milestone-evidence"><Check size={14} /><span><b>Evidence:</b> {milestone.evidence}</span></p>
          </div>
        </li>)}
      </ol>
    </section>

    <div className="project-spec-actions">
      {plan.runnable_project_id
        ? <button className="button button-primary" type="button" onClick={startAssessment} disabled={loading}>{loading ? <LoaderCircle className="spin" size={16} /> : <>Start graded assessment <ArrowRight size={16} /></>}</button>
        : <p>This is a portfolio brief. Automated grading is available only for the SQL revenue project.</p>}
    </div>
    {error && <div className="form-error" role="alert">{error}</div>}
  </section></AppShell>;
}
