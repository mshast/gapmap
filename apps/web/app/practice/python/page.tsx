"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, CirclePlay, CircleHelp, LoaderCircle, TriangleAlert, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { SqlEditor } from "@/components/SqlEditor";
import { useAppState } from "@/components/AppStateProvider";
import { preloadPython, pythonPractice, runPractice } from "@/lib/pythonPractice";

export default function PythonPracticePage() {
  const { state, setState, hydrated } = useAppState();
  const [taskIndex, setTaskIndex] = useState(0);
  const [pythonStatus, setPythonStatus] = useState<"loading" | "ready" | "failed">("loading");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const task = pythonPractice.tasks[taskIndex];
  const attempt = state.practice?.[task.id];
  const code = attempt?.code ?? task.starter;
  const run = attempt?.run ?? null;

  useEffect(() => {
    let active = true;
    preloadPython()
      .then(() => { if (active) setPythonStatus("ready"); })
      .catch(() => { if (active) setPythonStatus("failed"); });
    return () => { active = false; };
  }, []);

  function setAttempt(taskId: string, next: { code: string; run: typeof run }) {
    setState((current) => ({ ...current, practice: { ...current.practice, [taskId]: next } }));
  }

  async function check() {
    setError(""); setRunning(true);
    try {
      const result = await runPractice(code, task.cases);
      setAttempt(task.id, { code, run: result });
      setPythonStatus("ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your code could not run. Try again.");
    } finally { setRunning(false); }
  }

  if (!hydrated) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading saved session…</div></AppShell>;

  const passed = run?.results.filter((item) => item.passed).length ?? 0;
  const totals = pythonPractice.tasks.map((item) => {
    const results = state.practice?.[item.id]?.run?.results ?? [];
    return { id: item.id, passed: results.filter((result) => result.passed).length, total: item.cases.length };
  });

  return (
    <AppShell>
      <section className="page-wrap project-page">
        <div className="project-backline"><Link className="back-link" href={state.analysis ? "/readiness" : "/"}><ArrowLeft size={15} /> {state.analysis ? "Evidence map" : "Input"}</Link><span className="project-step">PYTHON PRACTICE / SELF-CHECKED</span></div>
        <div className="project-heading"><div><p className="eyebrow">PRACTICE EXERCISE · {pythonPractice.tasks.length} TASKS</p><h1>{pythonPractice.title}</h1><p className="intro-copy">{pythonPractice.scenario}</p></div><div className="project-stamp">PYTHON<br /><span>SELF-CHECKED</span></div></div>
        <div className="mock-banner"><CircleHelp size={16} /><span><b>Self-checked practice.</b> Your code runs only in this browser, so these checks are for your own practice. They don&apos;t change your evidence map and aren&apos;t graded by GapMap.</span></div>

        <div className="workspace-grid">
          <aside className="task-rail" aria-label="Practice tasks">
            <p className="eyebrow">TASKS / 0{pythonPractice.tasks.length}</p>
            {pythonPractice.tasks.map((item, index) => {
              const total = totals[index];
              return (
                <button key={item.id} className={`task-tab${index === taskIndex ? " selected" : ""}`} onClick={() => { setTaskIndex(index); setError(""); }} aria-current={index === taskIndex ? "step" : undefined}>
                  <span className="task-tab-number">0{index + 1}</span>
                  <span className="task-tab-title">{item.title}</span>
                  {total.passed === total.total && <Check className="task-tab-check" size={15} />}
                </button>
              );
            })}
            <div className="task-rail-note"><span className="rail-rule" />Code stays saved in this browser session.</div>
          </aside>

          <div className="workspace-main">
            <div className="task-prompt"><div><p className="eyebrow">TASK 0{taskIndex + 1} / {pythonPractice.tasks.length}</p><h2>{task.title}</h2></div><span className="task-competency">{task.cases.length} CHECKS</span></div>
            <p className="task-instructions">{task.instructions}</p>
            <div className="editor-toolbar"><span>CODE EDITOR <span className="editor-language">PYTHON</span></span><button className="text-button" type="button" onClick={() => setAttempt(task.id, { code: task.starter, run: null })}>Reset to starter</button></div>
            <SqlEditor language="python" label={`Python editor for ${task.title}`} value={code} onChange={(value) => setAttempt(task.id, { code: value, run })} />
            <div className="editor-actions">
              <button className="button button-primary" onClick={check} disabled={running || pythonStatus === "loading"}>{running ? <><LoaderCircle className="spin" size={16} /> Running checks</> : pythonStatus === "loading" ? <><LoaderCircle className="spin" size={16} /> Loading Python</> : <><CirclePlay size={16} /> Run checks</>}</button>
              {pythonStatus === "loading" && <span className="field-meta">First load downloads Python (about 10 MB).</span>}
            </div>
            {pythonStatus === "failed" && !running && <div className="form-error" role="alert"><TriangleAlert size={16} />Python could not load. Check your connection, then press Run checks to retry.</div>}
            {error && <div className="form-error" role="alert"><TriangleAlert size={16} />{error}</div>}

            {run && <section className="submission-section" aria-label="Check results">
              <div className="preview-heading"><div><p className="eyebrow">SELF-CHECK RESULTS</p><h3>{run.error ? "Your code did not run" : `${passed} of ${task.cases.length} checks passed`}</h3></div></div>
              {run.error ? <div className="form-error" role="alert"><TriangleAlert size={16} /><code>{run.error}</code></div> : <div className="feedback-list">{run.results.map((result) => <div className="feedback-item" key={result.label}>{result.passed ? <Check size={14} className="practice-pass" /> : <X size={14} className="practice-fail" />}<div><b>{result.label}</b>{result.message && <p><code>{result.message}</code></p>}</div></div>)}</div>}
            </section>}

            <div className="task-pagination"><span>{taskIndex + 1} of {pythonPractice.tasks.length}</span>{taskIndex < pythonPractice.tasks.length - 1 ? <button className="button button-text" onClick={() => { setTaskIndex((index) => index + 1); setError(""); }}>Next task <ArrowRight size={15} /></button> : <Link className="button button-text" href={state.analysis ? "/results" : "/"}>{state.analysis ? "Back to your plan" : "Analyze a role"} <ArrowRight size={15} /></Link>}</div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
