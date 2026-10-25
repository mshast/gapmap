"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, CircleHelp, LoaderCircle, MessageSquareText, TriangleAlert } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAppState } from "@/components/AppStateProvider";
import { SessionExpiredNotice, isSessionExpired } from "@/components/SessionExpiredNotice";
import { answerInterview, getInterviewSummary, isMockMode, startInterview } from "@/lib/api";
import type { InterviewQuestion, InterviewState } from "@/lib/types";

const typeLabels: Record<InterviewQuestion["type"], string> = {
  behavioral: "From your resume",
  technical: "From the posting",
  gap_probe: "On a gap",
};

const MAX_ANSWER = 3000;

export default function InterviewPage() {
  const { state, setState, hydrated } = useAppState();
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [busy, setBusy] = useState<"start" | "answer" | "summary" | null>(null);
  const [error, setError] = useState("");
  const analysis = state.analysis;
  const interview = state.interview;

  function updateInterview(update: (current: InterviewState) => InterviewState) {
    setState((current) => (current.interview ? { ...current, interview: update(current.interview) } : current));
  }

  async function begin() {
    if (!analysis) return;
    setError(""); setBusy("start");
    try {
      const started = await startInterview(analysis.session_id, analysis.analysis_id);
      setState((current) => ({
        ...current,
        interview: { id: started.interview_id, mode: started.mode, disclaimer: started.disclaimer, questions: started.questions, feedback: {}, drafts: {}, summary: null },
      }));
      setCurrentId(started.questions[0]?.id ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The interview could not start. Try again.");
    } finally { setBusy(null); }
  }

  async function submit(question: InterviewQuestion) {
    if (!interview) return;
    const text = (interview.drafts[question.id] ?? "").trim();
    if (!text) return;
    setError(""); setBusy("answer");
    try {
      const feedback = await answerInterview(interview.id, question.id, text);
      updateInterview((current) => {
        const questions = [...current.questions];
        // A follow-up is asked right after the question it follows.
        if (feedback.follow_up && feedback.follow_up_question_id && !questions.some((item) => item.id === feedback.follow_up_question_id)) {
          questions.splice(questions.findIndex((item) => item.id === question.id) + 1, 0, { ...question, id: feedback.follow_up_question_id, question: feedback.follow_up });
        }
        return { ...current, questions, feedback: { ...current.feedback, [question.id]: feedback }, summary: null };
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your answer could not be scored. Try again.");
    } finally { setBusy(null); }
  }

  async function loadSummary() {
    if (!interview) return;
    setError(""); setBusy("summary");
    try {
      const summary = await getInterviewSummary(interview.id);
      updateInterview((current) => ({ ...current, summary }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The summary could not be loaded. Try again.");
    } finally { setBusy(null); }
  }

  if (!hydrated) return <AppShell><div className="page-wrap loading-state"><LoaderCircle className="spin" /> Loading saved session…</div></AppShell>;
  if (!analysis) return <AppShell><div className="page-wrap empty-state"><h1>Start with a role.</h1><p>Interview questions come from your resume and the posting you analyze.</p><Link className="button button-primary" href="/">Go to input <ArrowRight size={16} /></Link></div></AppShell>;

  const questions = interview?.questions ?? [];
  const question = questions.find((item) => item.id === currentId) ?? questions.find((item) => !interview?.feedback[item.id]) ?? questions[0];
  const feedback = question ? interview?.feedback[question.id] : undefined;
  const answeredCount = Object.keys(interview?.feedback ?? {}).length;
  const nextQuestion = question ? questions.slice(questions.indexOf(question) + 1).find((item) => !interview?.feedback[item.id]) : undefined;
  const draft = question ? interview?.drafts[question.id] ?? "" : "";
  const wordCount = draft.trim().split(/\s+/).filter(Boolean).length;

  return (
    <AppShell>
      <section className="page-wrap interview-page">
        <div className="project-backline"><Link className="back-link" href="/readiness"><ArrowLeft size={15} /> Evidence map</Link><span className="project-step">PRACTICE / 05</span></div>
        <div className="stage-header"><div><p className="stage-kicker">PRACTICE · MOCK INTERVIEW</p><h1>Practice the questions this role will ask.</h1><p className="intro-copy">Five questions for <strong>{analysis.target_role}</strong>: two about work on your resume, two about the posting&apos;s requirements, and one about a gap. Each answer gets rubric feedback.</p></div>{interview && <div className="evidence-counter"><strong>{answeredCount}<span> / {questions.length}</span></strong><small>answered</small></div>}</div>

        {isMockMode && <div className="mock-banner"><CircleHelp size={16} /><span><b>Demo mode.</b> Questions and rubric scoring are based on the example role and your answers. Run the API with <code>NEXT_PUBLIC_GAPMAP_MOCK=false</code> for live AI generation.</span></div>}
        {interview?.mode === "demo" && <div className="mock-banner"><CircleHelp size={16} /><span><b>Demo interview.</b> Questions come from templates and scores come from simple text signals. No AI service ran.</span></div>}

        {!interview && <section className="project-callout"><span className="callout-index">05 /<br />PRACTICE</span><div className="callout-content"><p className="eyebrow">ABOUT 10 MINUTES</p><h2>Answer as you would in a real interview.</h2><p>Questions quote the exact resume line or posting text they come from. Feedback is practice only: it never changes your evidence or project score.</p></div><button className="button button-primary" type="button" onClick={begin} disabled={busy !== null}>{busy === "start" ? <><LoaderCircle className="spin" size={16} /> Writing questions</> : <>Start interview <ArrowRight size={16} /></>}</button></section>}

        {error && (isSessionExpired(error) ? <SessionExpiredNotice /> : <div className="form-error" role="alert"><TriangleAlert size={16} />{error}</div>)}

        {interview && question && (
          <div className="workspace-grid">
            <aside className="task-rail" aria-label="Interview questions">
              <p className="eyebrow">QUESTIONS / {questions.length}</p>
              {questions.map((item, index) => (
                <button key={item.id} className={`task-tab${item.id === question.id ? " selected" : ""}`} onClick={() => { setCurrentId(item.id); setError(""); }} aria-current={item.id === question.id ? "step" : undefined}>
                  <span className="task-tab-number">{item.id.endsWith("-followup") ? "↳" : `0${index + 1}`}</span>
                  <span className="task-tab-title">{item.id.endsWith("-followup") ? "Follow-up" : typeLabels[item.type]}</span>
                  {interview.feedback[item.id] && <Check className="task-tab-check" size={15} />}
                </button>
              ))}
              <div className="task-rail-note"><span className="rail-rule" />Answers and feedback stay saved in this browser session.</div>
            </aside>

            <div className="workspace-main">
              <div className="task-prompt"><div><p className="eyebrow">{question.id.endsWith("-followup") ? "FOLLOW-UP" : typeLabels[question.type].toUpperCase()}</p><h2 className="interview-question">{question.question}</h2></div><MessageSquareText size={18} /></div>
              <blockquote className="interview-grounding">{question.type === "behavioral" ? "Resume" : "Posting"}: “{question.grounding_quote}”</blockquote>

              {!feedback ? <>
                <label className="visually-hidden" htmlFor="answer-text">Your answer</label>
                <textarea id="answer-text" className="text-input" rows={9} maxLength={MAX_ANSWER} value={draft} placeholder="Type your answer as you would say it…" onChange={(event) => updateInterview((current) => ({ ...current, drafts: { ...current.drafts, [question.id]: event.target.value } }))} />
                <div className="textarea-foot"><span className="star-tip">Tip: Aim for 50–150 words using STAR (Situation, Task, Action, Result)</span><span>{wordCount} {wordCount === 1 ? "word" : "words"} · {draft.length.toLocaleString()} / {MAX_ANSWER.toLocaleString()}</span></div>
                <div className="editor-actions"><button className="button button-primary" type="button" onClick={() => submit(question)} disabled={busy !== null || !draft.trim()}>{busy === "answer" ? <><LoaderCircle className="spin" size={16} /> Scoring answer</> : <>Get feedback <ArrowRight size={16} /></>}</button></div>
              </> : <section className="submission-section" aria-label="Answer feedback">
                <div className="preview-heading"><div><p className="eyebrow">RUBRIC FEEDBACK</p><h3>How this answer reads</h3></div></div>
                <div className="interview-scores">{feedback.scores.map((score) => <div className="interview-score" key={score.criterion}><div className="interview-score-head"><span>{score.criterion}</span><strong>{score.score} / {score.max}</strong></div><p>{score.comment}</p>{score.answer_quote && <q>{score.answer_quote}</q>}</div>)}</div>
                <p className="eyebrow interview-subhead">IMPROVE IT</p>
                <ul className="interview-list">{feedback.improvements.map((item) => <li key={item}>{item}</li>)}</ul>
                <p className="eyebrow interview-subhead">SUGGESTED REWRITE</p>
                <blockquote className="interview-rewrite">{feedback.suggested_rewrite}</blockquote>
                <details className="interview-answer"><summary>Your answer</summary><p>{interview.drafts[question.id]}</p></details>
              </section>}

              <div className="task-pagination">
                <span>{answeredCount} of {questions.length} answered</span>
                {feedback?.follow_up_question_id && !interview.feedback[feedback.follow_up_question_id]
                  ? <button className="button button-text" onClick={() => setCurrentId(feedback.follow_up_question_id!)}>Answer the follow-up <ArrowRight size={15} /></button>
                  : nextQuestion && feedback && <button className="button button-text" onClick={() => setCurrentId(nextQuestion.id)}>Next question <ArrowRight size={15} /></button>}
                {answeredCount > 0 && <button className="button button-outline" onClick={loadSummary} disabled={busy !== null}>{busy === "summary" ? <><LoaderCircle className="spin" size={16} /> Summarizing</> : <>{interview.summary ? "Refresh summary" : "See summary"}</>}</button>}
              </div>
            </div>
          </div>
        )}

        {interview?.summary && (
          <section className="results-block interview-summary" aria-labelledby="summary-title">
            <div className="block-title"><div><p className="eyebrow">PRACTICE SUMMARY · {interview.summary.answered_count} OF {interview.summary.total_questions} ANSWERED</p><h2 id="summary-title">Where to focus next</h2></div></div>
            {interview.summary.criterion_averages.map((item) => <div className="competency-row" key={item.criterion}><span className="interview-criterion">{item.criterion}</span><span className="competency-points">{item.average.toFixed(1)} / {item.max}</span><span className="field-meta">{item.answers_scored} scored</span></div>)}
            {interview.summary.answered_count > 1 && <div className="interview-highlights">
              <div><p className="eyebrow">STRONGEST</p><p>{interview.summary.strongest_answer.question}</p></div>
              <div><p className="eyebrow">WEAKEST</p><p>{interview.summary.weakest_answer.question}</p></div>
            </div>}
            <ol className="interview-list">{interview.summary.practice_suggestions.map((item) => <li key={item}>{item}</li>)}</ol>
          </section>
        )}

        {interview && <p className="fixture-note">{interview.disclaimer}</p>}
      </section>
    </AppShell>
  );
}
