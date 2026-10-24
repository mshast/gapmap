# GapMap P0 Integration Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing analysis, SQL assessment, and readiness UI work end to end in the default application.

**Architecture:** Keep the current FastAPI service injection and generated contracts. Install the existing SQL service by default, send live PDFs to the existing multipart route, and make the results page use aggregated readiness evidence instead of duplicating backend rules.

**Tech Stack:** Python 3.12, FastAPI, pytest, Next.js 16, React 19, TypeScript.

**Spec:** `docs/superpowers/specs/2026-10-24-gapmap-p0-integration-repair-design.md`

## Global Constraints

- Add no dependencies.
- Preserve API contracts, SQL safety controls, hidden fixtures, and dependency injection.
- Do not modify or discard unrelated user changes.
- Keep sessions in memory and avoid live OpenAI calls during verification.

---

### Task 1: Install the SQL project service

**Files:**
- Modify: `gapmap/apps/api/main.py`
- Modify: `gapmap/apps/api/tests/test_routes.py`

**Interfaces:**
- Consumes: `SqlProjectService` implementing `ProjectService`.
- Produces: default `create_app()` project, preview, submit, and readiness behavior.

- [ ] **Step 1: Replace the placeholder route test**

Test that the default app returns `revenue-debug-001`, previews `SELECT 1 AS order_id, 'West' AS region, 100 AS amount_cents`, accepts a valid Task 1 query, and updates readiness.

- [ ] **Step 2: Run the route test and verify it fails**

Run: `.venv/bin/python -m pytest gapmap/apps/api/tests/test_routes.py -q`

Expected: FAIL because the default project service returns `501`.

- [ ] **Step 3: Install the existing service**

Import `SqlProjectService` in `main.py` and replace `UnavailableProjectService()` with `SqlProjectService()` when no service is injected.

- [ ] **Step 4: Run backend tests**

Run: `.venv/bin/python -m pytest`

Expected: all tests pass.

### Task 2: Repair frontend contract data and competency aggregation

**Files:**
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/app/results/page.tsx`

**Interfaces:**
- Consumes: generated `Analysis`, `Submission`, and `Readiness` types.
- Produces: contract-valid fixture data and correctly aggregated competency rows.

- [ ] **Step 1: Confirm the contract failure**

Run: `npm run typecheck --prefix apps/web`

Expected: FAIL because the mock analysis lacks `analysis_mode`.

- [ ] **Step 2: Repair fixture fields and IDs**

Add `analysis_mode: "demo"`, a fixture warning, and `resume_evidence` arrays to mock requirements. Replace every `refund_edge_cases` with `sql_refund_edge_cases`.

- [ ] **Step 3: Use readiness aggregation**

Build the result score map from `state.readiness.competency_evidence` when present. Otherwise sum matching competency scores across fixture submissions and derive `demonstrated_on_project`, `partially_demonstrated`, or `unverified` from all contributions.

- [ ] **Step 4: Run frontend typecheck**

Run: `npm run typecheck --prefix apps/web`

Expected: PASS.

### Task 3: Route live PDF analysis through the API

**Files:**
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/app/page.tsx`

**Interfaces:**
- Consumes: selected browser `File`, job description, and `/api/analyze/pdf`.
- Produces: `analyzePdf(file: File, jobDescription: string): Promise<Analysis>`.

- [ ] **Step 1: Add the multipart API call**

Create `analyzePdf` using `FormData` with `resume_file` and `job_description`; do not set the multipart content-type manually.

- [ ] **Step 2: Keep the selected file transient**

Store the selected file in page component state. Continue extracting text for preview and fixture mode, but call `analyzePdf` on live submission when a file is selected. Clear the selected file when the resume is edited, cleared, or replaced by the demo.

- [ ] **Step 3: Run frontend checks**

Run: `npm run typecheck --prefix apps/web && npm run lint --prefix apps/web`

Expected: PASS.

### Task 4: Update delivery documentation and verify the application

**Files:**
- Modify: `README.md`
- Modify: `demo/walkthrough.md`
- Verify: `gapmap/shared/contracts/openapi.json`
- Verify: `gapmap/shared/contracts/api.d.ts`

**Interfaces:**
- Consumes: actual default application behavior.
- Produces: accurate run and demo instructions.

- [ ] **Step 1: Remove stale placeholder claims**

Document that project detail, run, and submit are installed and that submissions update readiness.

- [ ] **Step 2: Regenerate contracts**

Run: `npm run contracts`

Expected: generated artifacts remain unchanged or contain only intentional contract changes.

- [ ] **Step 3: Run all quality gates**

Run: `.venv/bin/python -m pytest`

Run: `npm run typecheck --prefix apps/web`

Run: `npm run lint --prefix apps/web`

Run: `npm run build --prefix apps/web`

Expected: all commands pass.

- [ ] **Step 4: Run the offline smoke flow**

Start: `GAPMAP_DEMO_MODE=1 .venv/bin/python -m uvicorn gapmap.apps.api.main:app --port 8000`

Run: `.venv/bin/python scripts/smoke_analysis.py`

Expected: all smoke checks pass, then stop the server.

- [ ] **Step 5: Compare implementation to all four spec files**

Report each spec as met, partial, or missing, citing remaining gaps without expanding this repair's scope.
