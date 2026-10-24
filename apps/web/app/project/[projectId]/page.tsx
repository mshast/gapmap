"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, CirclePlay, LoaderCircle, Send, Table2, TriangleAlert } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { SqlEditor } from "@/components/SqlEditor";
import { useAppState } from "@/components/AppStateProvider";
import { getProject, getReadiness, isMockMode, runQuery, submitTask } from "@/lib/api";
import type { Project, ProjectTask, RunResult } from "@/lib/types";

export default function ProjectPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const { state, setState, hydrated } = useAppState();
  const [project, setProject] = useState<Project | null>(null);
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!hydrated) return;
    let active = true;
    getProject(projectId)
      .then((result) => { if (active) setProject(result); })
      .catch((caught: unknown) => { if (active) setError(caught instanceof Error ? caught.message : "Project could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [hydrated, projectId]);

  const task = project?.tasks[currentTaskIndex];
  const query = task ? state.queries[task.id] ?? task.starter_sql : "";
  const preview = task ? state.previews[task.id] : undefined;
  const submission = task ? state.submissions[task.id] : undefined;

  function setQuery(taskId: string, value: string) {
    setState((current) => ({ ...current, queries: { ...current.queries, [taskId]: value } }));
  }

  async function runPreview() {
    if (!task || !state.analysis) return;
    setRunning(true); setError(""); setNotice("");
    try {
      const result = await runQuery(projectId, state.analysis.session_id, task.id, query);
      setState((current) => ({ ...current, previews: { ...current.previews, [task.id]: result } }));
      if (result.error) setError(result.error);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Query could not run. Try again.");
    } finally {
      setRunning(false);
    }
  }

  async function submit() {
    if (!task || !state.analysis) return;
    setSubmitting(true); setError(""); setNotice("");
    try {
      const result = await submitTask(projectId, state.analysis.session_id, task.id, query);
      setState((current) => ({ ...current, readiness: null, submissions: { ...current.submissions, [task.id]: result } }));
      setNotice(isMockMode ? "Fixture response saved. This is not an evaluation of your SQL." : "Submission evaluated and saved.");
      if (!isMockMode) {
        try {
          const readiness = await getReadiness(state.analysis.session_id);
          setState((current) => ({ ...current, readiness }));
        } catch {
          setError("Submission saved. Open Results to retry refreshing your evidence.");
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Submission could not be evaluated. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function renderPreview(result: RunResult) {
    if (result.error) return <div className="result-error"><TriangleAlert size={16} />{result.error}</div>;
    return (
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>{result.rows.slice(0, 20).map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={`${rowIndex}-${cellIndex}`}>{cell === null ? <span className="null-cell">NULL</span> : String(cell)}</td>)}</tr>)}</tbody>
        </table>
        {result.rows.length === 0 && <p className="empty-result">Query returned no rows.</p>}
        {result.truncated && <p className="field-meta">Preview limited to the first 20 rows.</p>}
      </div>
    );
  }

  if (!hydrated || loading) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading project…</div></AppShell>;
  if (!state.analysis) return <AppShell><div className="page-wrap empty-state"><h1>No active session.</h1><p>Analyze a role before opening its project.</p><Link className="button button-primary" href="/">Go to input <ArrowRight size={16} /></Link></div></AppShell>;
  if (error && !project) return <AppShell><div className="page-wrap empty-state"><p className="eyebrow">PROJECT UNAVAILABLE</p><h1>Could not open this work sample.</h1><p>{error}</p><button className="button button-outline" onClick={() => window.location.reload()}>Retry</button></div></AppShell>;
  if (!project || !task) return null;

  return (
    <AppShell>
      <section className="page-wrap project-page">
        <div className="project-backline"><Link className="back-link" href="/readiness"><ArrowLeft size={15} /> Evidence map</Link><span className="project-step">SQL WORK SAMPLE / 03</span></div>
        <div className="project-heading"><div><p className="eyebrow">MINI PROJECT · {project.competencies.length} COMPETENCIES</p><h1>{project.title}</h1><p className="intro-copy">{project.scenario}</p></div><div className="project-stamp">GAPMAP<br /><span>FIELD NOTE 001</span></div></div>
        {isMockMode && <div className="mock-banner"><TriangleAlert size={16} /><span><b>Fixture mode.</b> Query previews and submission feedback are examples, not execution or grading of your SQL.</span></div>}

        <details className="schema-panel" open>
          <summary><Table2 size={15} /> Schema reference</summary>
          <pre>{project.schema_text}</pre>
        </details>

        <div className="workspace-grid">
          <aside className="task-rail" aria-label="Project tasks">
            <p className="eyebrow">TASKS / 03</p>
            {project.tasks.map((item: ProjectTask, index) => (
              <button key={item.id} className={`task-tab${index === currentTaskIndex ? " selected" : ""}`} onClick={() => { setCurrentTaskIndex(index); setError(""); setNotice(""); }} aria-current={index === currentTaskIndex ? "step" : undefined}>
                <span className="task-tab-number">0{index + 1}</span>
                <span className="task-tab-title">{item.title}</span>
                {state.submissions[item.id] && <Check className="task-tab-check" size={15} />}
              </button>
            ))}
            <div className="task-rail-note"><span className="rail-rule" />Draft queries stay saved in this browser session.</div>
          </aside>

          <div className="workspace-main">
            <div className="task-prompt"><div><p className="eyebrow">TASK 0{currentTaskIndex + 1} / {project.tasks.length}</p><h2>{task.title}</h2></div><span className="task-competency">{task.expected_columns.join(" · ")}</span></div>
            <p className="task-instructions">{task.instructions}</p>
            <div className="editor-toolbar"><span>QUERY EDITOR <span className="editor-language">SQL</span></span><button className="text-button" type="button" onClick={() => setQuery(task.id, task.starter_sql)}>Reset to starter</button></div>
            <SqlEditor label={`SQL editor for ${task.title}`} value={query} onChange={(value) => setQuery(task.id, value)} />
            <div className="editor-actions"><button className="button button-outline" onClick={runPreview} disabled={running || submitting}>{running ? <><LoaderCircle className="spin" size={16} /> Running</> : <><CirclePlay size={16} /> Run preview</>}</button><button className="button button-primary" onClick={submit} disabled={submitting || running}>{submitting ? <><LoaderCircle className="spin" size={16} /> Sending</> : <><Send size={15} /> Submit for evaluation</>}</button></div>
            {error && <div className="form-error" role="alert"><TriangleAlert size={16} />{error}<button className="text-button" onClick={runPreview}>Retry preview</button></div>}
            {notice && <div className="success-note" role="status"><Check size={16} />{notice}<Link href="/results">View results <ArrowRight size={14} /></Link></div>}
            {preview && <section className="preview-section"><div className="preview-heading"><div><p className="eyebrow">PREVIEW RESULT</p><h3>Visible sample only</h3></div><span>{preview.rows.length} rows</span></div>{renderPreview(preview)}<p className="preview-caveat">A preview confirms the query can return rows. It is not a grading verdict.</p></section>}
            {submission && <section className="submission-section"><div className="preview-heading"><div><p className="eyebrow">SUBMISSION FEEDBACK</p><h3>{submission.task_score.earned} / {submission.task_score.possible} points</h3></div><span className="status-pill status-partially_demonstrated">{submission.task_id}</span></div><div className="feedback-list">{submission.public_test_feedback.map((item) => <div className="feedback-item" key={item.label}><span className={`feedback-mark${item.passed ? " passed" : " failed"}`}>{item.passed ? <Check size={13} /> : <TriangleAlert size={13} />}</span><div><b>{item.label}</b><p>{item.explanation}</p></div></div>)}</div></section>}
            <div className="task-pagination"><span>{currentTaskIndex + 1} of {project.tasks.length}</span>{currentTaskIndex < project.tasks.length - 1 ? <button className="button button-text" onClick={() => { setCurrentTaskIndex((index) => index + 1); setError(""); setNotice(""); }}>Next task <ArrowRight size={15} /></button> : <Link className="button button-text" href="/results">Project results <ArrowRight size={15} /></Link>}</div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
