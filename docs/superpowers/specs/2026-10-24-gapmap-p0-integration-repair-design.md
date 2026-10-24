# GapMap P0 Integration Repair Design

## Goal

Make the existing GapMap analysis, SQL project, grading, and results code work as one default end-to-end application while keeping the current contracts and dependencies.

## Scope

- Install `SqlProjectService` in the default FastAPI application while preserving test injection.
- Replace placeholder route expectations with an end-to-end project test covering project load, preview, submission, and readiness recomputation.
- Bring frontend mock analysis data back into the generated API contract by adding `analysis_mode`, `warnings`, and required resume evidence fields.
- Use the canonical `sql_refund_edge_cases` competency ID everywhere.
- Aggregate competency evidence across tasks. In live mode, use `/api/readiness` as the source of truth; in fixture mode, sum saved submission scores.
- Submit selected PDFs to `/api/analyze/pdf` in live mode so server limits and errors apply. Keep text analysis unchanged and keep fixture mode local.
- Update README claims that the project endpoints still return `501`.

## Data Flow

Text input continues through `POST /api/analyze`. A selected live PDF is stored only in component state and sent with the job description as multipart data to `POST /api/analyze/pdf`; it is not written to local storage. Analysis creates the existing in-memory session. Project preview and submission use the already implemented SQL service, and submission results update that session. The results page refreshes readiness and renders its aggregated competency evidence.

## Error Handling and Safety

Existing FastAPI validation, PDF limits, SQLite authorizer, execution limits, sanitized SQL errors, and session checks remain unchanged. The frontend continues to show API errors with retry paths. No raw resume, PDF bytes, hidden fixtures, or canonical SQL are added to logs or responses.

## Tests and Verification

- Backend: run the complete pytest suite and update integration route coverage for the real default project service.
- Contracts: regenerate and verify OpenAPI-derived TypeScript types remain current.
- Frontend: run typecheck, lint, and production build.
- Demo: run the existing smoke script against a locally started demo API, including analysis, project access, grading, and readiness update where practical.

## Explicit Non-Goals

- No durable database; sessions still reset when the API process restarts.
- No new frontend testing framework or dependency.
- No redesign, authentication, arbitrary projects, or changes to grading rules.
- No live OpenAI request during automated verification.
