"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, LoaderCircle } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAppState } from "@/components/AppStateProvider";
import { getProject } from "@/lib/api";
import { findPlan } from "@/lib/projectPlans";

export default function ProjectPlanPage({ params }: { params: Promise<{ planId: string }> }) {
  const { planId } = use(params);
  const { state, setState, hydrated } = useAppState();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const analysis = state.analysis;
  const readiness = state.readiness?.session_id === analysis?.session_id ? state.readiness : null;
  const requirements = readiness?.requirements ?? analysis?.requirements ?? [];
  const plan = findPlan(requirements, planId);

  async function startAssessment() {
    if (!plan?.runnableProjectId) return;
    setError("");
    setLoading(true);
    try {
      const project = await getProject(plan.runnableProjectId);
      setState((current) => ({ ...current, project }));
      router.push(`/project/${project.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The graded assessment could not be loaded.");
      setLoading(false);
    }
  }

  if (!hydrated) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading project plan…</div></AppShell>;
  if (!analysis) return <AppShell><div className="page-wrap empty-state"><p className="eyebrow">PROJECT PLAN</p><h1>Start with a role.</h1><p>Your project plan is built from the gaps in a saved role analysis.</p><Link className="button button-primary" href="/">Go to input <ArrowRight size={16} /></Link></div></AppShell>;
  if (!plan) return <AppShell><div className="page-wrap empty-state"><p className="eyebrow">PROJECT PLAN</p><h1>This plan is no longer available.</h1><p>The analysis may have changed. Return to your evidence map to choose a current recommendation.</p><Link className="button button-primary" href="/readiness">Back to evidence map <ArrowRight size={16} /></Link></div></AppShell>;

  return <AppShell><section className="page-wrap project-spec-page">
    <div className="project-backline"><Link className="back-link" href="/readiness"><ArrowLeft size={15} /> Evidence map</Link><span className="project-step">PROJECT SPEC</span></div>
    <header className="project-spec-header"><p className="stage-kicker">TARGETED TO {analysis.target_role}</p><h1>{plan.title}</h1><p className="intro-copy">{plan.why}</p></header>
    <div className="project-spec-grid">
      <section className="project-spec-block"><p className="eyebrow">DELIVERABLE</p><h2>What you will ship</h2><p>{plan.deliverable}</p><div className="project-spec-skills"><span>Skills this demonstrates</span><strong>{plan.skills.join(" · ")}</strong></div></section>
      <section className="project-spec-block"><p className="eyebrow">BUILD PLAN</p><h2>Milestones and completion checks</h2><ol className="project-spec-steps">{plan.steps.map((step, index) => <li key={step}><span className="project-spec-number">0{index + 1}</span><div><strong>{step}</strong><span><Check size={14} /> Complete when this milestone is working and documented.</span></div></li>)}</ol></section>
    </div>
    <div className="project-spec-actions">{plan.runnableProjectId ? <button className="button button-primary" type="button" onClick={startAssessment} disabled={loading}>{loading ? <LoaderCircle className="spin" size={16} /> : <>Start graded assessment <ArrowRight size={16} /></>}</button> : <p>This project is a guided portfolio plan. Automated grading is not available for it yet.</p>}</div>
    {error && <div className="form-error" role="alert">{error}</div>}
  </section></AppShell>;
}
