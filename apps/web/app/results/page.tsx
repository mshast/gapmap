"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, CircleHelp, LoaderCircle, Target } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { StatusPill } from "@/components/StatusPill";
import { useAppState } from "@/components/AppStateProvider";
import { getReadiness, isMockMode } from "@/lib/api";
import type { EvidenceStatus } from "@/lib/types";

const skillLabels: Record<string, string> = {
  sql_joins: "Joins",
  sql_filtering: "Filtering",
  sql_aggregation: "Aggregation",
  refund_edge_cases: "Refund edge cases",
};

export default function ResultsPage() {
  const { state, setState, hydrated } = useAppState();
  const [loading, setLoading] = useState(!isMockMode);
  const [apiError, setApiError] = useState("");
  const analysis = state.analysis;
  const tasks = state.project?.tasks ?? [];
  const submissions = Object.values(state.submissions);
  const scoreBySkill = useMemo(() => {
    const scores = new Map<string, { earned: number; possible: number; status: EvidenceStatus }>();
    for (const submission of submissions) {
      for (const score of submission.competency_scores) {
        scores.set(score.skill_id, { earned: score.earned, possible: score.possible, status: score.status });
      }
    }
    return scores;
  }, [submissions]);
  const totalEarned = submissions.reduce((sum, item) => sum + item.task_score.earned, 0);
  const totalPossible = tasks.length ? tasks.reduce((sum, task) => sum + (state.submissions[task.id]?.task_score.possible ?? 0), 0) : 0;
  const submittedCount = submissions.length;

  useEffect(() => {
    if (!hydrated || isMockMode || !analysis?.session_id) return;
    let active = true;
    getReadiness(analysis.session_id)
      .then((readiness) => { if (active) setState((current) => ({ ...current, readiness })); })
      .catch((caught: unknown) => { if (active) setApiError(caught instanceof Error ? caught.message : "Readiness could not be refreshed."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [analysis?.session_id, hydrated, setState]);

  function statusAfter(skillIds: string[], before: EvidenceStatus): EvidenceStatus {
    const relevant = skillIds.map((skillId) => scoreBySkill.get(skillId)).filter((score) => score !== undefined);
    if (!relevant.length) return before;
    if (relevant.length === skillIds.length && relevant.every((score) => score.status === "demonstrated_on_project")) return "demonstrated_on_project";
    if (relevant.some((score) => score.status === "demonstrated_on_project" || score.status === "partially_demonstrated")) return "partially_demonstrated";
    return before;
  }

  if (!hydrated) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading saved results…</div></AppShell>;
  if (!analysis) return <AppShell><div className="page-wrap empty-state"><h1>No results yet.</h1><p>Start with a role and build a work sample.</p><Link className="button button-primary" href="/">Go to input <ArrowRight size={16} /></Link></div></AppShell>;

  const roadmap = state.readiness?.roadmap ?? analysis.roadmap ?? [];

  return (
    <AppShell>
      <section className="page-wrap results-page">
        <div className="project-backline"><Link className="back-link" href="/project/revenue-debug-001"><ArrowLeft size={15} /> Project workspace</Link><span className="project-step">EVIDENCE UPDATE / 04</span></div>
        <div className="results-heading"><div><p className="eyebrow"><span className="eyebrow-line" /> WORK SAMPLE SUMMARY</p><h1>Progress you<br /><em>can point to.</em></h1><p className="intro-copy">A narrow sample of your work, not a hiring prediction.</p></div><div className="score-plate"><span className="score-label">PROJECT POINTS</span><strong>{totalEarned}<span> / {tasks.length ? "100" : "—"}</span></strong><span className="score-caption">{submittedCount} of {tasks.length || 3} tasks submitted</span></div></div>

        {isMockMode && <div className="mock-banner"><CircleHelp size={16} /><span><b>Demo fixture results.</b> These are prewritten examples and do not grade the SQL submitted in this browser.</span></div>}
        {apiError && <div className="form-error" role="alert">{apiError} <button className="text-button" onClick={() => window.location.reload()}>Retry</button></div>}
        {loading && <p className="field-meta"><LoaderCircle className="spin" size={14} /> Refreshing readiness from the API…</p>}

        <div className="results-grid">
          <section className="results-block task-results">
            <div className="block-title"><div><p className="eyebrow">TASK OUTCOMES</p><h2>Submission record</h2></div><span className="block-count">{submittedCount} / {tasks.length || 3}</span></div>
            {(tasks.length ? tasks : [{ id: "t1", title: "Connect orders to customer regions" }, { id: "t2", title: "Find gross revenue by region" }, { id: "t3", title: "Account for refunds" }]).map((task) => {
              const result = state.submissions[task.id];
              return <article className="outcome-row" key={task.id}><div className={`outcome-icon${result ? " has-result" : ""}`}>{result ? <Check size={15} /> : <span>—</span>}</div><div className="outcome-main"><h3>{task.title}</h3>{result ? <><p>{result.task_score.earned} / {result.task_score.possible} points · {result.task_id}</p>{result.public_test_feedback.map((feedback) => <span className={`case-label${feedback.passed ? " passed" : ""}`} key={feedback.label}>{feedback.passed ? "Passed" : "Needs work"}: {feedback.label}</span>)}</> : <p className="not-submitted">Not submitted</p>}</div><Link href={`/project/${analysis.recommended_project_id ?? "revenue-debug-001"}`} aria-label={`Review ${task.title}`}><ArrowRight size={16} /></Link></article>;
            })}
            <div className="outcome-total"><span>Scored tasks total</span><strong>{totalEarned} / {totalPossible || 100}</strong></div>
          </section>

          <section className="results-block competency-results">
            <div className="block-title"><div><p className="eyebrow">TESTED COMPETENCIES</p><h2>What this sample covered</h2></div><Target size={18} /></div>
            {["sql_joins", "sql_filtering", "sql_aggregation", "refund_edge_cases"].map((skillId) => {
              const score = scoreBySkill.get(skillId);
              return <div className="competency-row" key={skillId}><span>{skillLabels[skillId]}</span>{score ? <><span className="competency-points">{score.earned} / {score.possible}</span><StatusPill status={score.status} /></> : <span className="not-submitted">Not assessed</span>}</div>;
            })}
            <p className="scope-note">Passing one SQL sample does not certify broader skill or predict job performance.</p>
          </section>
        </div>

        <section className="evidence-trail">
          <div className="block-title"><div><p className="eyebrow">BEFORE / AFTER</p><h2>Requirement evidence trail</h2></div><Link className="subtle-link" href="/readiness">Full evidence map <ArrowRight size={14} /></Link></div>
          <div className="trail-header"><span>REQUIREMENT</span><span>BEFORE WORK SAMPLE</span><span>AFTER WORK SAMPLE</span></div>
          {analysis.requirements.map((requirement) => {
            const after = statusAfter(requirement.skill_ids, requirement.evidence_status);
            return <div className="trail-row" key={requirement.id}><span className="trail-requirement">{requirement.label}</span><span><StatusPill status={requirement.evidence_status} /></span><span><StatusPill status={after} /></span></div>;
          })}
        </section>

        <section className="roadmap-band"><div><p className="eyebrow">NEXT STEPS / IN PRIORITY ORDER</p><h2>Keep building evidence.</h2></div><ol>{roadmap.slice(0, 3).map((item, index) => <li key={`${item.requirement_id}-${item.priority}`}><span className="roadmap-index">0{index + 1}</span><span>{item.action}</span></li>)}</ol></section>
      </section>
    </AppShell>
  );
}