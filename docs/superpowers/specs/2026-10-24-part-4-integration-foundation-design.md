# Part 4 Integration Foundation Design

## Goal

Build the contract-first backend foundation for GapMap so the frontend, analysis, and SQL project workstreams can integrate against stable APIs without Part 4 taking ownership of their internal implementations.

## Scope

This phase creates the FastAPI application skeleton, canonical Pydantic contracts, deterministic demo fixture, session persistence boundary, OpenAPI and TypeScript contract artifacts, integration tests, and exact local run documentation.

The foundation provides working health, fixture, analysis, project recommendation, and readiness flows using explicitly labeled deterministic adapters. The SQL project detail, run, and submission routes are present in the API contract but return a clear `501 Not Implemented` response until Part 3 supplies its registry and grader. PDF analysis is also deferred because it is a P1 capability owned by Part 2.

## Architecture

The application uses an app factory in `gapmap/apps/api/main.py`. The factory constructs shared state, injects service adapters, configures development CORS, and mounts all routes under `/api`. Imports remain side-effect-light so tests can create isolated applications.

Canonical request and response models live in `gapmap/apps/api/contracts.py`. Route handlers, tests, and generated artifacts all derive from those models. The checked-in OpenAPI snapshot is the machine-readable contract, while generated TypeScript declarations under `gapmap/shared/contracts/` give the frontend stable names without copying interfaces by hand.

Analysis and project behavior sit behind narrow Python protocols. The initial analysis adapter recognizes only the canonical demo fixture and is clearly identified as deterministic demo behavior. It returns grounded quotes copied from the fixture and never claims that an AI provider ran. Part 2 can replace this adapter through dependency injection. The project adapter exposes recommendation lookup now; Part 3 can supply project metadata, execution, and grading later without changing HTTP shapes.

## Components and Responsibilities

### API entrypoint

`main.py` owns application construction, middleware, exception behavior, dependency wiring, and router registration. CORS allows the documented local frontend origins only. `/api/health` remains independent of downstream adapters.

### Shared contracts

`contracts.py` defines constrained Pydantic models for every stable route in spec 04, including enums for evidence status, verification capability, and requirement type. Input text is stripped, must be non-empty, and has explicit length limits. IDs, scores, priorities, result rows, and task collections receive structural constraints. Public submission feedback cannot represent hidden fixture rows, oracle SQL, or exact hidden expected results.

### Service boundaries

`services/interfaces.py` defines the asynchronous analysis and project service protocols consumed by routes. Adapters return contract models rather than untyped dictionaries. Unavailable project operations raise a typed capability error that the API maps to `501` with a stable, readable detail message.

### Demo fixture and deterministic adapter

The fixture is stored as ordinary text assets and loaded through one fixture module. It describes an engineering student with Python project experience and no SQL claim, paired with an internship posting containing exact SQL, Docker, and React requirements. The deterministic adapter emits traceable substring quotes, maps SQL to `revenue-debug-001`, leaves SQL `unverified`, and marks Docker and React verification capability `not_assessable`.

### Session store

The first implementation uses a single-process, lock-protected in-memory store and documents that sessions reset whenever the API process restarts. It stores analyses by analysis ID, session state by session ID, original ordered requirements, and the latest successful submission for each `(project_id, task_id)` pair.

The store exposes focused operations rather than its internal dictionaries. Replacing a task attempt recomputes project and competency totals from active attempts, so repeated submissions never add points. Requirement status recomputation considers only mapped skill IDs. A requirement becomes `demonstrated_on_project` only when all assessable required subskills are demonstrated; a passing subset yields `partially_demonstrated`. Uncovered subskills prevent full demonstration. Skills such as React and Docker can never inherit evidence from SQL scoring.

### Generated contracts

A repository script creates `openapi.json` from the app factory and emits TypeScript declarations from the OpenAPI component schemas using a pinned development tool. Contract generation is deterministic. A test regenerates into a temporary directory and compares the result with checked-in artifacts so drift fails CI.

## Route Behavior

- `GET /api/health` returns `{ "status": "ok" }`.
- `GET /api/demo/fixture` returns the canonical resume and job description.
- `POST /api/analyze` validates inputs, calls the analysis adapter, creates a session, and returns stable UUID-backed analysis data.
- `GET /api/projects/recommended?analysis_id=...` returns the stored recommendation and a deterministic reason; an unknown analysis returns `404`.
- `GET /api/readiness?session_id=...` derives requirements, competency evidence, roadmap, and current project total from session state; an unknown session returns `404`.
- `GET /api/projects/{id}`, `POST /api/projects/{id}/run`, and `POST /api/projects/{id}/submit` are contract-complete placeholders that return `501` until a project service with those capabilities is injected.
- `/api/analyze/pdf` is not added in this foundation because the stable spec calls it optional and assigns PDF extraction to Part 2.

## Data Flow

The frontend fetches the canonical fixture and submits it to `/api/analyze`. The route validates the request, calls the deterministic analysis adapter, and persists the returned requirements and recommendation in a new session. The response gives the frontend both `session_id` and `analysis_id`. Recommendation lookup resolves through stored analysis state. Readiness lookup recomputes its response from the session's original requirements and active submissions on every request, keeping the roadmap consistent with evidence.

When Part 3 arrives, a successful grader result is passed to the session store only after grading completes. The store replaces that task's active attempt, recomputes totals and per-skill status, and retains no grader secrets in the public response.

## Error Handling and Trust Boundaries

Malformed path/query/body input uses FastAPI's `422` response. Unknown session, analysis, or project identifiers use `404`. A defined but unavailable capability uses `501`; unexpected adapter failures use `503` with no resume text, job text, SQL, stack trace, API key, or hidden fixture details in the response.

Resume and posting text are always treated as data. The deterministic adapter matches fixture content and ignores instructions embedded within it. No input can change the skill taxonomy, scoring rules, capability flags, or route behavior. Request bodies and raw resumes are not logged by application code.

## Testing

Tests use `pytest`, FastAPI's test client, and isolated application instances. Coverage includes:

- validation of empty and oversized analysis inputs;
- exact response schemas and enum values for every route;
- fixture quote grounding against normalized source text;
- prompt-injection text failing to modify fixed evidence behavior;
- SQL remaining unverified and Docker/React remaining not assessable in the demo;
- missing session and analysis `404` responses;
- unavailable project operations returning sanitized `501` responses;
- latest-attempt overwrite rather than additive scoring;
- competency and multi-skill requirement recomputation without cross-skill leakage;
- roadmap priority ordering and advancement after relevant evidence changes;
- OpenAPI and generated TypeScript artifact drift.

Part 3 remains responsible for safe SQL execution, hidden fixtures, deterministic grading, and the double-counting cases. Part 2 remains responsible for general AI analysis, PDF extraction, and quote verification beyond the fixed fixture.

## Delivery and Documentation

The root README gives exact commands to create a virtual environment, install pinned dependencies, run tests, regenerate contracts, and start the API. It lists every supported environment variable; this foundation requires none. It explicitly warns that in-memory sessions reset on restart and distinguishes deterministic demo mode from real AI analysis.

The demo directory contains the canonical input fixture and a walkthrough aligned with the required three-minute sequence. Recording, deployment credentials, and final submission are operational follow-ups, not generated claims of completion.

## Deferred Work

- General LLM-backed analysis and PDF extraction: Part 2.
- SQL project registry, public fixture, safe executor, hidden grading, and real project routes: Part 3.
- Next.js dashboard and interaction behavior: Part 1.
- Durable SQLite session persistence: optional upgrade after the in-memory integration path is stable.
- Deployment and recorded video: performed after all workstreams integrate.

## Acceptance Criteria

The foundation is complete when a clean checkout can install dependencies, run the full foundation test suite, start the API, retrieve the fixture, analyze it, fetch its recommendation and readiness state, and reproduce checked-in OpenAPI and TypeScript contracts. All unavailable Part 2 or Part 3 capabilities are explicit, stable, and non-deceptive.
