"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Check, FileText, LoaderCircle, Sparkles, Upload, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAppState } from "@/components/AppStateProvider";
import { analyze, analyzePdf, getDemoFixture, isMockMode } from "@/lib/api";
import { extractPdfText } from "@/lib/pdf";

export default function HomePage() {
  const router = useRouter();
  const { state, setState, hydrated } = useAppState();
  const fileInput = useRef<HTMLInputElement>(null);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [fileLabel, setFileLabel] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  async function loadDemo() {
    setError("");
    setLoadingDemo(true);
    try {
      const fixture = await getDemoFixture();
      setState((current) => ({
        ...current,
        resumeText: fixture.resume_text,
        jobText: fixture.job_description,
      }));
      setFileLabel("");
      setResumeFile(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Demo example could not be loaded.");
    } finally {
      setLoadingDemo(false);
    }
  }

  async function onFileSelected(file?: File) {
    if (!file) return;
    setError("");
    if (file.size > 5 * 1024 * 1024) {
      setError("Choose a PDF smaller than 5 MB, or paste your resume text.");
      return;
    }
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file. You can also paste resume text below.");
      return;
    }
    try {
      const text = await extractPdfText(file);
      setState((current) => ({ ...current, resumeText: text }));
      setFileLabel(file.name);
      setResumeFile(file);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not read this PDF. Paste your resume text instead.");
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setAnalyzing(true);
    try {
      const result = resumeFile && !isMockMode
        ? await analyzePdf(resumeFile, state.jobText)
        : await analyze(state.resumeText, state.jobText);
      setState((current) => ({ ...current, analysis: result, project: null, readiness: null, previews: {}, submissions: {} }));
      router.push("/readiness");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not analyze these inputs. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  }

  const canAnalyze = state.resumeText.trim().length > 0 && state.jobText.trim().length > 0;

  return (
    <AppShell>
      <section className="page-wrap input-page">
        <div className="intro-band">
          <div>
            <p className="eyebrow"><span className="eyebrow-line" /> EVIDENCE BUILDER / 01</p>
            <h1>Make your next<br /><em>move visible.</em></h1>
            <p className="intro-copy">Bring a resume and a real role. GapMap finds the evidence you already have, then helps you build what is missing.</p>
          </div>
          <div className="intro-aside" aria-label="Workflow steps">
            <span className="aside-number">01—04</span>
            <span>Read the role.<br />Build one useful proof.</span>
          </div>
        </div>

        <form className="input-grid" onSubmit={onSubmit}>
          <section className="input-panel resume-panel" aria-labelledby="resume-heading">
            <div className="panel-heading">
              <div className="panel-number">A</div>
              <div>
                <p className="eyebrow">YOUR STARTING POINT</p>
                <h2 id="resume-heading">Resume</h2>
              </div>
              <FileText className="panel-icon" size={19} />
            </div>
            <p className="field-hint">Upload a text-based PDF or paste the text below. A missing mention is not a verdict on your ability.</p>
            <div className="upload-row">
              <input ref={fileInput} className="visually-hidden" type="file" accept="application/pdf,.pdf" onChange={(event) => onFileSelected(event.target.files?.[0])} />
              <button className="button button-outline button-small" type="button" onClick={() => fileInput.current?.click()}>
                <Upload size={15} /> Choose PDF
              </button>
              {fileLabel && <span className="file-confirm"><Check size={14} /> {fileLabel}</span>}
              <span className="field-meta">PDF · max 5 MB</span>
            </div>
            <label className="visually-hidden" htmlFor="resume-text">Resume text</label>
            <textarea
              id="resume-text"
              className="text-input resume-input"
              value={state.resumeText}
              onChange={(event) => {
                setState((current) => ({ ...current, resumeText: event.target.value }));
                setFileLabel("");
                setResumeFile(null);
              }}
              placeholder="Paste resume text here…"
              rows={11}
              maxLength={50000}
            />
            <div className="textarea-foot"><span>{state.resumeText.length.toLocaleString()} / 50,000</span>{state.resumeText && <button className="text-button" type="button" onClick={() => { setState((current) => ({ ...current, resumeText: "" })); setFileLabel(""); setResumeFile(null); }}>Clear</button>}</div>
          </section>

          <section className="input-panel job-panel" aria-labelledby="job-heading">
            <div className="panel-heading">
              <div className="panel-number">B</div>
              <div>
                <p className="eyebrow">THE ROLE YOU WANT</p>
                <h2 id="job-heading">Job posting</h2>
              </div>
              <Sparkles className="panel-icon" size={19} />
            </div>
            <p className="field-hint">Paste the full posting so each requirement can stay tied to its original wording.</p>
            <div className="text-only-label">TEXT ONLY <span>Paste from the employer’s listing</span></div>
            <label className="visually-hidden" htmlFor="job-text">Job posting text</label>
            <textarea
              id="job-text"
              className="text-input job-input"
              value={state.jobText}
              onChange={(event) => setState((current) => ({ ...current, jobText: event.target.value }))}
              placeholder="Paste job description here…"
              rows={14}
              maxLength={50000}
            />
            <div className="textarea-foot"><span>{state.jobText.length.toLocaleString()} / 50,000</span>{state.jobText && <button className="text-button" type="button" onClick={() => setState((current) => ({ ...current, jobText: "" }))}>Clear</button>}</div>
          </section>

          <div className="form-actions">
            <button className="button button-text" type="button" onClick={loadDemo} disabled={loadingDemo}>
              {loadingDemo ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />}
              Load demo example
            </button>
            <div className="submit-actions">
              <span className="submit-note">{isMockMode ? "Using labeled demo fixtures" : "Connected to GapMap API"}</span>
              <button className="button button-primary" type="submit" disabled={!canAnalyze || analyzing || !hydrated}>
                {analyzing ? <><LoaderCircle className="spin" size={17} /> Reading inputs</> : <>Analyze evidence <ArrowRight size={17} /></>}
              </button>
            </div>
          </div>
          {error && <div className="form-error" role="alert"><X size={16} />{error}</div>}
        </form>
      </section>
    </AppShell>
  );
}
