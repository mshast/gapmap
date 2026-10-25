# GapMap

GapMap turns a resume and a real job posting into an evidence map, a project plan, and a graded work sample. A resume keyword is a claim; a measured result is evidence. GapMap keeps those separate and shows what to build next.

Five steps, one session:

1. **Input** — paste a resume (or upload a text PDF) and a posting.
2. **Readiness** — every requirement is quoted from the posting, matched against resume claims, and marked as tested or still unverified.
3. **Projects** — each gap gets a milestone-level project brief, plus one project GapMap can actually grade.
4. **Assessment / practice** — run and submit SQL against hidden test data, or self-check a Python exercise in the browser.
5. **Results** — graded competency scores, a changed evidence trail, and the next actions in priority order.

A mock interview runs alongside the flow and is grounded in the same analysis.

## Repository layout

| Path | What lives there |
| --- | --- |
| `apps/web/` | Next.js 16 app (App Router, client-rendered flow, session in `localStorage`) |
| `gapmap/apps/api/` | FastAPI service: analysis, project briefs, graded SQL project, mock interview |
| `gapmap/shared/contracts/` | Checked-in `openapi.json` and generated `api.d.ts` |
| `scripts/` | Contract export, contract generation, offline smoke check |
| `demo/` | Recording script, canonical resume/posting, architecture slide |
| `specs/`, `docs/superpowers/` | Product specs and design/implementation notes |

## Requirements

- Python 3.12
- Node.js 20 or newer
- npm

## Install

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
npm install
npm install --prefix apps/web
```

## Generate shared contracts

```bash
npm run contracts
```

This rewrites:

- `gapmap/shared/contracts/openapi.json`
- `gapmap/shared/contracts/api.d.ts`

Both are checked in. `gapmap/apps/api/tests/test_contract_artifacts.py` fails when the snapshot no longer matches the application.

## Run the checks

```bash
.venv/bin/python -m pytest
npm run typecheck --prefix apps/web
npm run lint --prefix apps/web
npm run build --prefix apps/web
```

The backend suite runs offline with deterministic fixtures and mocked provider responses, and needs no API key. It covers quote grounding, contextual versus keyword-only resume claims, the skill taxonomy, prompt injection, provider failures, PDF parsing and limits, project briefs (generation, caching, grounding, fallback, quota), interview generation and scoring, the interview demo fallback, SQL grading, readiness, and the contract artifacts.

## Run locally

Start the API in deterministic demo mode:

```bash
GAPMAP_DEMO_MODE=1 .venv/bin/python -m uvicorn gapmap.apps.api.main:app --reload --port 8000
```

Start the web app against the API (not the in-browser fixtures):

```bash
NEXT_PUBLIC_GAPMAP_MOCK=false npm run dev --prefix apps/web
```

Open <http://localhost:3000>. The top-right chip should read **API connected**; **Demo fixtures** means the browser is serving its own bundled example and nothing reaches the API.

- CORS accepts the web app at `http://localhost:3000` and `http://127.0.0.1:3000`, so start it on port 3000 (the `dev` script's default). A different port needs the allowlist in `gapmap/apps/api/main.py` updated.
- `apps/web/next.config.ts` proxies `/api/*` to `GAPMAP_API_URL` (default `http://127.0.0.1:8000`), so the browser talks to one origin.
- Sessions live in the API's memory. Restarting the API forgets every analysis, project attempt, and interview; load the page again and start from the input step.

Useful API entry points while it runs:

- Health: <http://localhost:8000/api/health>
- Interactive docs: <http://localhost:8000/docs>

### Offline smoke check

With the API in demo mode:

```bash
.venv/bin/python scripts/smoke_analysis.py
```

It expects three `PASS` lines and five grounded requirements: SQL starts `unverified` and Python starts as a resume claim, React and Docker are `not_assessable`, a contextual SQL line becomes `resume_evidence`, and an injected instruction changes nothing.

## The web app

| Route | Purpose |
| --- | --- |
| `/` | Input: resume text or PDF, posting, `Analyze evidence` (live) and `Demo analysis` (provider-free) |
| `/readiness` | Requirement-by-requirement evidence map, project plans, tailored project briefs |
| `/projects/[planId]` | One project brief: scenario, inputs, outputs, constraints, deliverables, milestones, tests, evidence |
| `/project/[projectId]` | The graded SQL workspace (Monaco editor, preview, submit, per-task feedback) |
| `/practice/python` | Self-checked Python exercise that runs only in the browser |
| `/interview` | Mock interview for the current analysis, with rubric feedback and a summary |
| `/results` | Project score, changed evidence, next actions, copyable plan and print view |

`Demo fixtures` mode (`NEXT_PUBLIC_GAPMAP_MOCK` unset, or `true`) renders the bundled example entirely in the browser, including requirements, briefs, grading, and interview heuristics. It labels every fixture and makes no API call. `Demo analysis` on the input page is different: it calls `POST /api/analyze/demo`, so the analysis is real and the pasted resume is still evaluated — useful when the provider key is out of credits but the SQL workspace and interview still need a live session.

## Analysis

`POST /api/analyze` sends the resume and posting to the configured provider for one structured extraction. Everything after extraction is deterministic server code.

- Both inputs are capped at 50,000 characters and cannot be blank. PDFs are capped at 5 MiB, 20 pages, and 50,000 extracted characters; extraction uses `pypdf`, closes temporary uploads, and does no OCR.
- Live extraction proposes every material requirement in the posting, capped at 12. Job and resume quotes are verified as source substrings (whitespace-insensitive), unsupported or duplicate excerpts are dropped, posting order is restored, and fewer than five grounded requirements is a `503` rather than padded output.
- The fixed taxonomy is `sql_joins`, `sql_filtering`, `sql_aggregation`, `sql_refund_edge_cases`, `python`, `react`, `docker`, `dsa`, and `other`. Generic SQL maps to joins/filtering/aggregation; refund cases require explicit context. Synonyms are canonicalized and tags are reconciled against the quoted text.
- `resume_quotes` holds contextual claims only. `resume_evidence` records them with `source_type: resume_claim` and `strength: contextual` or `keyword_only`; a bare keyword never establishes usage.
- `verification_capability` is independent of `evidence_status`. A React claim can be `resume_evidence` while being `not_assessable`, and a mixed requirement exposes its uncovered skills instead of inheriting SQL credit.
- Initial analysis can only emit `unverified` or `resume_evidence`. Only measured project results advance an item to `partially_demonstrated` or `demonstrated_on_project`.
- Identical resume/posting pairs reuse their extraction in memory (`GAPMAP_ANALYSIS_CACHE_SIZE`, `0` disables), so a retake costs nothing and returns the same result. The cache never outlives the process.

## Project briefs

`GET /api/project-briefs?session_id=...&analysis_id=...` returns up to four briefs for the highest-priority gaps in stored roadmap order. Each is grounded in the exact posting quote and the requirement's canonical skills, and carries a scenario, inputs, outputs, constraints, deliverables, and three to five milestones with work, acceptance criteria, tests, and evidence.

- SQL gaps always receive the existing graded `revenue-debug-001` brief; it is the only automatically graded project. Generated briefs never claim grading.
- `POST /api/project-briefs/generate` makes one batched structured request for the non-SQL gaps and caches the result in the session. Reloading the readiness page or reopening a brief makes no provider call.
- A provider failure, a `429`, an oversized bounded request, or invalid/ungrounded output returns the deterministic briefs with a warning and is not cached, so an explicit retry can try again. Invalid structured output is retried at most once; a `429` is never retried.
- Only the target role, requirement ids, labels, types, exact quotes, and canonical skills reach the provider. Resume text and interview answers never do.
- Titles that merely restate a technology, invented requirement ids, missing edge-case tests, and grading claims are rejected deterministically, and the affected gap falls back to its deterministic brief.
- Demo mode and a missing provider key never call out. Briefs never change readiness or competency evidence.

## Graded SQL project

`revenue-debug-001` is an e-commerce revenue investigation with three tasks. `POST /api/projects/{id}/run` previews a query read-only on public fixture data (capped at 20 rows); `POST /api/projects/{id}/submit` grades it against hidden fixtures and records the latest attempt per task.

Task 3 is the real defect: the dashboard query joins refunds directly, so an order with multiple refunds is counted twice. Aggregating refunds per order first, and labeling customers without a region as `Unknown`, passes all cases. Task 1 and task 2 award 35 and 25 points; task 3 is worth 40. Submissions are per session, and readiness recomputes competency evidence from them.

## Mock interview

The interview uses the stored analysis requirements, never the raw resume or posting text. `POST /api/interview/start` returns five questions, targeting two behavioral questions grounded in resume quotes, two technical questions grounded in posting quotes, and one gap probe for an unverified requirement. When a resume has fewer distinct grounded experiences, the shortfall is filled with technical questions, so the set is still five. Every grounding quote is verified server-side; invented requirements, unsupported quotes, and accusing gap probes are rejected.

Answers are scored 1–4 on relevance, specificity, structure, impact, and accuracy (technical questions only). Every cited answer quote is checked against the submitted text, and one follow-up is allowed per main question. `GET /api/interview/{interview_id}/summary` averages the criteria, credits the strongest and weakest answers, and returns three practice suggestions. Interview feedback never changes readiness or competency evidence.

Demo interview mode is explicit and independent of fixture mode:

- `{"mode": "demo"}` on `POST /api/interview/start`, or **Use demo mode** on `/interview`.
- `GAPMAP_INTERVIEW_MODE=demo` makes every interview deterministic.
- With the default `auto`, a `402`/`429` while generating questions or scoring an answer switches that interview to demo, keeps submitted answers, and labels the remaining feedback as demo.
- `GAPMAP_INTERVIEW_MODE=live` disables the fallback and surfaces the provider error as `503`.

Demo interviews still read the current analysis, so questions stay grounded in the actual resume and posting with no provider call. Scores come from deterministic text signals and the page says so.

## Configuration

Copy `.env.example` to `.env` (ignored by Git) and start the API with `--env-file .env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GAPMAP_DEMO_MODE` | disabled | `1`, `true`, or `yes` selects deterministic fixture analysis and makes no AI call. Only the bundled posting is accepted. |
| `GAPMAP_INTERVIEW_MODE` | `auto` | `auto` falls back to a labeled demo interview on a quota/rate-limit error; `live` keeps it a `503`; `demo` never calls a provider. |
| `GAPMAP_LLM_PROVIDER` | `openai` | `openai`, `groq`, `ollama`, or `demo` (no provider configured). |
| `OPENAI_API_KEY` | unset | Required for `GAPMAP_LLM_PROVIDER=openai`. Server-side only. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Structured-output model for extraction. |
| `GROQ_API_KEY` | unset | Required for `GAPMAP_LLM_PROVIDER=groq`. Server-side only. |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq structured-output model. |
| `GROQ_REASONING_EFFORT` | `low` | Reasoning effort for gpt-oss models; low uses about half the tokens of medium. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL. |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local Ollama model for extraction. |
| `GAPMAP_ANALYSIS_CACHE_SIZE` | `32` | In-memory extraction cache entries for identical resume/posting pairs; `0` disables. |
| `GAPMAP_API_URL` | `http://127.0.0.1:8000` | Web app: where `/api/*` is proxied. |
| `NEXT_PUBLIC_GAPMAP_MOCK` | `true` | Web app: set to `false` to use the API instead of browser fixtures. |

Without a configured key, analysis returns an actionable `503`. Provider failures, refusals, invalid schemas, or fewer than five grounded requirements also return `503`. There is no silent fallback: demo analysis must be enabled explicitly and only accepts the bundled posting, and an arbitrary posting is never replaced with fixture results. Health checks and fixture retrieval work without a key.

Both provider clients share the same strict JSON schema and Pydantic validation. Ollama receives the resume and posting only for extraction; quote grounding, scoring, and project recommendations stay server-side.

## Implemented routes

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/health` | No key required |
| GET | `/api/demo/fixture` | Bundled resume and posting |
| POST | `/api/analyze` | `{resume_text, job_description}` |
| POST | `/api/analyze/demo` | Provider-free analysis of the bundled posting with the supplied resume |
| POST | `/api/analyze/pdf` | Multipart `resume_file` + `job_description` |
| GET | `/api/readiness` | `?session_id=` |
| GET | `/api/projects/recommended` | `?analysis_id=` |
| GET | `/api/projects/{project_id}` | Project metadata and tasks |
| POST | `/api/projects/{project_id}/run` | `{session_id, task_id, sql}`: read-only preview, 20-row cap |
| POST | `/api/projects/{project_id}/submit` | Same body: graded on hidden fixtures |
| GET | `/api/project-briefs` | `?session_id=&analysis_id=`: cached or deterministic briefs, never a provider call |
| POST | `/api/project-briefs/generate` | `{session_id, analysis_id}`: one batched provider request per analysis |
| POST | `/api/interview/start` | `{session_id, analysis_id, mode?}`; `mode: "demo"` skips the provider |
| POST | `/api/interview/{interview_id}/answer` | `{question_id, answer_text}` |
| GET | `/api/interview/{interview_id}/summary` | Averages, highlights, practice suggestions |

## Evidence and integration rules

The analysis boundary is `StructuredAnalysisService.analyze(resume_text, job_text) -> AnalysisResult` in `gapmap/apps/api/services/analysis/`. `AnalysisResult` aliases the shared `AnalysisDraft`; the session store adds session and analysis UUIDs. `services/projects/registry.py` holds only the fixed `revenue-debug-001` metadata and its four SQL competency ids.

Readiness and analysis share one roadmap algorithm: descending `importance * evidence_gap_factor`, with factors 2 for unverified, 1 for resume-only or partial evidence, and 0 for demonstrated. Ties keep posting order, and `priority` is the resulting one-based rank. Unassessable requirements receive portfolio or learning actions with no verification call to action.

## Limitations and privacy

Live extraction and self-reported claims can be incomplete or mistaken. Context checks are conservative English heuristics, so unusual wording, negation, or skills outside the taxonomy may stay unverified. A posting needs at least five distinct requirements, and the service handles one internship posting per request. Unsupported skills map to `other` and have no assessment.

Resumes and postings are untrusted data: they cannot choose endpoints or tools, run instructions, or set scores or project results. Raw inputs are not logged or stored by the API; only short evidence excerpts and derived analysis remain in the in-memory session, and PDF bytes are discarded after extraction. Provider-side handling follows the configured API account, and disabling response storage is not a claim of zero provider retention. The session store is single-process and in memory, so a restart clears all state; a durable store can replace it behind the same interface.

Graded results describe one narrow work sample. GapMap does not predict employability or job-placement odds.

## Demo

`demo/` holds the recording outline (`walkthrough.md`), the canonical resume and posting, and the architecture slide. The fixture resume intentionally has no SQL claim; the labeled five-requirement extraction fixture is `services/analysis/fixtures/demo_extraction.json`, and its job quotes are exact substrings of the bundled posting.
