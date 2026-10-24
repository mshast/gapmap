# JobFinder — Part 4 of 4: Shared Contracts, Integration, Testing, and HackOHI/O Delivery

## Codex assignment
You are integration lead. Own `apps/api/main.py`, shared contract/schema definitions, session state, end-to-end tests, fixtures coordination, README, deployment, and demo preparation. Coordinate with Parts 1–3; avoid rewriting their internal modules. Establish shared API shapes **first** so all four workstreams can proceed in parallel.

## Monorepo layout
```
jobfinder/
  apps/web/                 # Part 1 Next.js
  apps/api/main.py          # Part 4 FastAPI entrypoint
  apps/api/services/analysis/   # Part 2
  apps/api/services/projects/   # Part 3
  apps/api/session_store.py # Part 4
  apps/api/tests/           # cross-service / end-to-end
  shared/contracts/         # Part 4 JSON Schema or OpenAPI-derived TS types
  demo/                     # sample resume, posting, demo walkthrough
  README.md
```

## Stable REST contracts
Set API base path `/api` and CORS for the dev frontend. JSON content types except optional PDF upload route.

**POST `/api/analyze`** accepts JSON `{ "resume_text": string, "job_description": string }`; PDF upload can use `/api/analyze/pdf` multipart `{resume_file,job_description}`. Returns:
```json
{
  "session_id": "uuid",
  "analysis_id": "uuid",
  "target_role": "Software Engineering Intern",
  "requirements": [
    {
      "id": "req-sql",
      "label": "SQL relational querying",
      "job_quote": "Experience with SQL databases",
      "importance": 3,
      "requirement_type": "required",
      "skill_ids": ["sql_joins", "sql_filtering", "sql_aggregation"],
      "resume_quotes": [],
      "evidence_status": "unverified",
      "verification_capability": "available"
    }
  ],
  "recommended_project_id": "revenue-debug-001",
  "roadmap": [{"requirement_id":"req-sql","action":"Complete revenue debugging project","priority":1}]
}
```
`verification_capability` is `available` or `not_assessable`; distinct from `evidence_status`. `evidence_status` ∈ `unverified | resume_evidence | partially_demonstrated | demonstrated_on_project`.

**GET `/api/demo/fixture`** -> `{resume_text,job_description}` for reliable demo mode.

**GET `/api/projects/recommended?analysis_id=...`** -> `{project_id: string|null, reason: string}`.

**GET `/api/projects/{id}`** -> `{id,title,scenario,schema_text,tasks:[{id,title,instructions,expected_columns,starter_sql}],competencies:[string]}`. Three task IDs: `t1`, `t2`, `t3`.

**POST `/api/projects/{id}/run`** `{session_id,task_id,sql}` -> `{columns:[string],rows:[[number|string|null]],truncated:boolean,error:string|null}`.

**POST `/api/projects/{id}/submit`** `{session_id,task_id,sql}` -> `{submission_id,task_id,task_score:{earned:number,possible:number},competency_scores:[{skill_id,earned,possible,status}],public_test_feedback:[{label,passed,explanation}]}`. Do not expose hidden dataset or oracle source.

**GET `/api/readiness?session_id=...`** -> `{session_id,requirements:[same requirement shape with updated statuses],competency_evidence:[{skill_id,status,earned,possible,source_project_id}],roadmap:[{requirement_id,action,priority}],project_total:{earned,possible}}`.

**GET `/api/health`** -> `{status:"ok"}`.

## Session store and consistency
- Use SQLite session persistence or a single-process in-memory store with explicit warning that sessions reset on restart. For hackathon deployment choose SQLite (durable) if trivial, otherwise memory is acceptable with stable demo video.
- Store original requirement IDs, resume evidence, project submissions per task, scoring by competency, and roadmap derivation.
- Submission overwrite: latest successful grading run of each task is the active attempt. Recompute cumulative project score from current attempt per task (not additive across repeated submissions).
- Compute `demonstrated_on_project` from competency tests only. Never mark unrelated `react`/`docker` requirements demonstrated after SQL tasks.
- Requirement evidence status should be based on the specific mapped skill set; when a requirement includes multiple skills, mark fully demonstrated only when all its *assessable required subskills* pass, and disclose uncovered subskills. Better default: a requirement with uncovered subskills cannot be fully demonstrated.

## Integration order / parallel working agreement
1. Part 4 commits project skeleton, Pydantic models, OpenAPI routes/stubs, sample fixture, and generated TS client types.
2. Part 1 builds against those types and mock API responses.
3. Part 2 connects job/resume analysis and curated project matching.
4. Part 3 connects real SQL engine, tests, and submits scored results.
5. Part 4 wires persistence, recomputation, e2e tests, and deployment.

## Demonstration scenario (must pass)
- Fixture resume: engineering student with Python/project experience but **no SQL mention**.
- Fixture SWE internship posting: SQL essential, plus Docker/React as additional requirements (uncovered by the mini-project).
- Dashboard: SQL `unverified`, Docker and React `not_assessable` for verification.
- Run incorrect T3 SQL that double-counts multi-refund orders; grading flags failed cases.
- Run corrected SQL; grader accepts and updates SQL refund competency; roadmap moves to next unmet requirement.
- Show traceable job quotes, project result evidence, and explicit constraints; do not imply job placement odds.

## Automated quality gates
- Backend: `pytest` covering schema validation, quote grounding, project matching, safe SQL execution, hidden fixtures, double-counting, and cumulative status recompute.
- Frontend: typecheck, build, interaction smoke tests with mocked backend; one real API e2e test if time permits.
- API contracts: OpenAPI snapshot/types match frontend; 422 validation errors have readable UI messages.
- Security: prompt-injection input doesn't modify scoring; SQL DDL, multi-statement, ATTACH, infinite queries denied; no API keys in frontend.
- Reliability: demo works from clean start with no manual DB editing; happy path completes in <3 minutes of recorded screen time.

## Time-boxed priorities
**P0:** contracts and fixtures, input→analysis→evidence dashboard, SQL project, run/submit, deterministic score, roadmap update, stable demo video.
**P1:** PDF parser fallback, nuanced candidate evidence, better errors, polished UI, multiple fixtures, explanation transparency.
**P2 / cut:** voice interview, external job scraping, accounts, payments, arbitrary AI-generated projects, Python sandbox, GitHub integration, application automation.

## HackOHI/O rules and presentation
- Open Challenge: show Innovation, Curiosity, Communication, Project Breadth & Complexity, Impact, and Growth Mindset (navigating challenges).
- Event keynote: hacking ends Sunday Oct 25, 2026 at 10:00 AM; 3-minute demo video required. Record and prepare ahead of the deadline.
- 3-minute video outline: 0:00–0:20 problem; 0:20–0:45 sample resume/posting; 0:45–1:05 traced gaps; 1:05–1:35 personalized project; 1:35–2:10 failing then passing SQL assessment; 2:10–2:35 changed evidence/roadmap; 2:35–3:00 architecture, impact, authentic challenge/lesson.
- No made-up user impact or unverifiable accuracy claims. Explain that work sample results evidence narrow competencies, not employability.

## Definition of done
- [ ] Fully working end-to-end demo without manually editing state.
- [ ] All 3 SQL tasks have real execution and deterministic tests.
- [ ] No hallucinated job/resume quotes or unsupported readiness scores.
- [ ] Verified competency results and roadmap recompute persisted correctly.
- [ ] Invalid input, AI/API failure, unsafe SQL handled gracefully.
- [ ] `README.md` has exact install/run commands and environment variable names.
- [ ] Three-minute recorded demo is available and submission completed on time.
