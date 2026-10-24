# Project Details and Groq Interviews Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make posting-grounded project recommendations browsable and make the existing mock-interview API run safely through the configured Groq provider.

**Architecture:** Keep project specifications deterministic and client-side, using the existing `plansForRequirements` output as the only source for both cards and detail pages. Reuse the analysis provider convention for the interview client, wire the existing interview service into the FastAPI factory, and enforce `(session_id, analysis_id)` ownership in the shared session store.

**Tech Stack:** Next.js 16, React 19, TypeScript, FastAPI, Pydantic, HTTPX, Pytest

**Spec:** `docs/superpowers/specs/2026-10-24-project-details-and-groq-interviews-design.md`

## Global Constraints

- Keep `revenue-debug-001` as the only executable, automatically graded project.
- Do not edit environment files or add dependencies.
- Interview feedback must never alter competency evidence.
- Provider errors and logs must not expose provider bodies, resumes, or answers.
- Missing project state must show a recovery path and must not silently substitute the SQL project.

---

### Task 1: Enforce Analysis Ownership for Interviews

**Files:**
- Modify: `gapmap/apps/api/session_store.py`
- Modify: `gapmap/apps/api/services/interview/store.py`
- Test: `gapmap/apps/api/services/interview/tests/test_interview_routes.py`

**Interfaces:**
- Produces: `InMemorySessionStore.requirements_for(session_id: UUID, analysis_id: UUID) -> list[Requirement] | None`
- Consumes: `SessionStoreAnalysisSource.load_requirements(session_id, analysis_id)`

- [ ] **Step 1: Write the failing cross-session ownership test**

Add a test that creates two analyses, then pairs the first session with the second analysis:

```python
def test_interview_rejects_analysis_owned_by_another_session(make_api, analyzed):
    client, _ = make_api(DemoInterviewClient())
    with client:
        first = analyzed(client)
        second = analyzed(client)
        response = client.post("/api/interview/start", json={
            "session_id": first["session_id"],
            "analysis_id": second["analysis_id"],
        })
    assert response.status_code == 404
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `.venv/bin/python -m pytest gapmap/apps/api/services/interview/tests/test_interview_routes.py::test_interview_rejects_analysis_owned_by_another_session -q`

Expected: FAIL because the current source independently accepts both valid IDs.

- [ ] **Step 3: Add one paired lookup to the shared store**

Add the narrow method under `recommendation_for`:

```python
def requirements_for(self, session_id: UUID, analysis_id: UUID) -> list[Requirement] | None:
    with self._lock:
        session = self._sessions.get(session_id)
        if session is None or session.analysis.analysis_id != analysis_id:
            return None
        return [item.model_copy(deep=True) for item in session.analysis.requirements]
```

Replace the independent lookups in `SessionStoreAnalysisSource`:

```python
def load_requirements(self, session_id: UUID, analysis_id: UUID) -> list[Requirement] | None:
    return self._session_store.requirements_for(session_id, analysis_id)
```

- [ ] **Step 4: Run the focused interview route tests**

Run: `.venv/bin/python -m pytest gapmap/apps/api/services/interview/tests/test_interview_routes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gapmap/apps/api/session_store.py gapmap/apps/api/services/interview/store.py gapmap/apps/api/services/interview/tests/test_interview_routes.py
git commit -m "fix: bind interviews to analysis sessions"
```

### Task 2: Use the Configured Hosted Provider for Interviews

**Files:**
- Modify: `gapmap/apps/api/services/interview/llm_client.py`
- Test: `gapmap/apps/api/services/interview/tests/test_interview_routes.py`
- Test: `gapmap/apps/api/services/interview/tests/test_interview_injection.py`

**Interfaces:**
- Modifies: `InterviewLLMClient(api_key, model, *, base_url, transport)`
- Produces: `client_from_env()` with `groq`, `openai`, and explicit demo selection matching analysis conventions

- [ ] **Step 1: Write failing provider-selection tests**

Add tests that clear provider variables and assert Groq configuration without exposing the key:

```python
def test_environment_selects_groq(monkeypatch):
    monkeypatch.setenv("GAPMAP_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.delenv("GAPMAP_DEMO_MODE", raising=False)
    client = client_from_env()
    assert isinstance(client, InterviewLLMClient)
    assert client._base_url == "https://api.groq.com/openai/v1/chat/completions"
    assert client._model == "openai/gpt-oss-20b"
```

Update the missing-key test to expect a provider-neutral message such as `GROQ_API_KEY` when Groq is selected.

- [ ] **Step 2: Run the provider tests and verify they fail**

Run: `.venv/bin/python -m pytest gapmap/apps/api/services/interview/tests/test_interview_routes.py -q`

Expected: FAIL because the client always uses OpenAI variables and endpoint.

- [ ] **Step 3: Parameterize the endpoint and mirror analysis provider selection**

Change the constructor and request target:

```python
def __init__(
    self,
    api_key: str,
    model: str = "gpt-4o-mini",
    *,
    base_url: str = "https://api.openai.com/v1/chat/completions",
    key_name: str = "OPENAI_API_KEY",
    transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    self._api_key = api_key
    self._model = model
    self._base_url = base_url
    self._key_name = key_name
    self._transport = transport
```

Post to `self._base_url`, and make the missing-key error name `self._key_name`. Implement `client_from_env` with the same `GAPMAP_LLM_PROVIDER`, `GROQ_API_KEY`, `GROQ_MODEL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` choices as `StructuredAnalysisService.from_env`. Raise `ValueError` for unsupported providers; retain explicit `GAPMAP_DEMO_MODE` handling. Do not add Ollama support to interviews because the requested live provider is Groq and the interview client depends on OpenAI-compatible structured output.

- [ ] **Step 4: Verify provider payload safety and selection**

Run: `.venv/bin/python -m pytest gapmap/apps/api/services/interview/tests/test_interview_routes.py gapmap/apps/api/services/interview/tests/test_interview_injection.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gapmap/apps/api/services/interview/llm_client.py gapmap/apps/api/services/interview/tests/test_interview_routes.py gapmap/apps/api/services/interview/tests/test_interview_injection.py
git commit -m "fix: use configured provider for interviews"
```

### Task 3: Install the Interview Service in the Real API

**Files:**
- Modify: `gapmap/apps/api/main.py`
- Modify: `gapmap/apps/api/tests/test_routes.py`

**Interfaces:**
- Modifies: `create_app(..., interview_service: InterviewService | None = None) -> FastAPI`
- Consumes: one shared `InMemorySessionStore` instance and `InterviewService.from_env(store)`

- [ ] **Step 1: Write a failing real-app route test**

Add a test using the ordinary `client` fixture:

```python
def test_interview_route_is_installed(client: TestClient) -> None:
    response = client.get("/api/interview/00000000-0000-0000-0000-000000000000/summary")
    assert response.status_code == 404
```

The expected result distinguishes an installed service (`404`) from the router's not-installed response (`501`) or a missing route (`404` with FastAPI's generic body); also assert the body detail is `Interview not found.`.

- [ ] **Step 2: Run the test and verify it fails**

Run: `.venv/bin/python -m pytest gapmap/apps/api/tests/test_routes.py::test_interview_route_is_installed -q`

Expected: FAIL because the interview router is not included.

- [ ] **Step 3: Wire one store and the interview router**

In `create_app`, resolve the session store once before assigning app state:

```python
store = session_store or InMemorySessionStore()
application.state.session_store = store
application.state.interview_service = interview_service or InterviewService.from_env(store)
```

Import and include the interview router after the main router:

```python
application.include_router(router)
application.include_router(interview_router)
```

Keep dependency injection optional so tests can provide a fake service without provider calls.

- [ ] **Step 4: Run API route and interview tests**

Run: `.venv/bin/python -m pytest gapmap/apps/api/tests/test_routes.py gapmap/apps/api/services/interview/tests -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gapmap/apps/api/main.py gapmap/apps/api/tests/test_routes.py
git commit -m "fix: install mock interview API"
```

### Task 4: Add Stable Project-Spec Lookup and Details

**Files:**
- Modify: `apps/web/lib/projectPlans.ts`
- Create: `apps/web/app/projects/[planId]/page.tsx`
- Modify: `apps/web/app/globals.css`

**Interfaces:**
- Produces: `findPlan(requirements: Requirement[], planId: string) -> ProjectPlan | undefined`
- Consumes: `AppState.analysis`, current readiness requirements, `getProject`, and existing `ProjectPlan`

- [ ] **Step 1: Add the stable lookup**

Export the existing plan lookup without duplicating plan generation:

```typescript
export function findPlan(requirements: Requirement[], planId: string) {
  return plansForRequirements(requirements, false).find((plan) => plan.id === planId);
}
```

- [ ] **Step 2: Create the project-spec detail page**

Create a client page that reads `planId` with React's `use(params)`, resolves requirements from readiness or analysis, and renders the existing plan fields. Its states must be:

```tsx
if (!hydrated) return <AppShell>...Loading project plan…</AppShell>;
if (!analysis) return <AppShell>...Go to input…</AppShell>;
if (!plan) return <AppShell>...Back to evidence map…</AppShell>;
```

Render `plan.why`, `plan.deliverable`, and `plan.steps`; present each step as both a milestone and its completion checklist item. If `plan.runnableProjectId` exists, load it with the existing `getProject`, save it through `setState`, and navigate to `/project/${project.id}`. Otherwise show no grading claim.

- [ ] **Step 3: Add only page-specific layout rules**

Reuse existing typography, buttons, `page-wrap`, labels, and spacing. Add a small `.project-spec-*` group only for the detail grid/checklist and responsive collapse; do not create a new visual system.

- [ ] **Step 4: Run frontend static checks**

Run: `npm --prefix apps/web run typecheck`

Expected: PASS.

Run: `npm --prefix apps/web run lint`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/projectPlans.ts apps/web/app/projects/'[planId]'/page.tsx apps/web/app/globals.css
git commit -m "feat: add project recommendation details"
```

### Task 5: Link Recommendation Cards to Their Details

**Files:**
- Modify: `apps/web/app/readiness/page.tsx`
- Modify: `apps/web/app/results/page.tsx`

**Interfaces:**
- Consumes: `/projects/${plan.id}` from every recommendation card
- Preserves: SQL detail page's separate graded-assessment action

- [ ] **Step 1: Replace inert readiness actions with detail links**

Every card gets a visible link:

```tsx
<Link className="button button-outline" href={`/projects/${plan.id}`}>
  View project plan <ArrowRight size={15} />
</Link>
```

Remove the readiness page's direct SQL loading function and local loading state because the detail page owns that action.

- [ ] **Step 2: Link results recommendations the same way**

Replace the conditional retry-only link with the same detail link for all plans. The SQL detail page will expose the retry/start action.

- [ ] **Step 3: Run frontend checks**

Run: `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build`

Expected: all commands PASS and Next.js lists `/projects/[planId]`.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/readiness/page.tsx apps/web/app/results/page.tsx
git commit -m "fix: make project recommendations browsable"
```

### Task 6: Put Interview Tests in the Default Suite and Verify Everything

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Modifies: Pytest discovery only; no runtime behavior

- [ ] **Step 1: Prove interview tests are absent from ordinary collection**

Run: `.venv/bin/python -m pytest --collect-only -q | rg "interview"`

Expected before the change: no collected interview tests.

- [ ] **Step 2: Expand test discovery narrowly**

Set:

```toml
testpaths = [
  "gapmap/apps/api/tests",
  "gapmap/apps/api/services/projects/tests",
  "gapmap/apps/api/services/interview/tests",
]
```

- [ ] **Step 3: Run the complete backend and frontend verification**

Run: `.venv/bin/python -m pytest`

Expected: PASS with interview and project-service tests collected.

Run: `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build`

Expected: PASS.

- [ ] **Step 4: Confirm environment files were untouched**

Run: `git status --short && git diff -- .env apps/web/.env.local apps/web/.env.example`

Expected: no environment-file diff.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "test: include service suites by default"
```

## Final Review

- Confirm a real analyzed posting produces recommendation cards that open distinct detail URLs and preserve each exact job quote.
- Confirm the SQL detail can open the existing graded assessment while non-SQL details make no grading claim.
- Confirm a Groq-backed interview start reaches the configured endpoint and returns five grounded questions.
- Confirm cross-session analysis IDs return a sanitized `404`.
- Confirm `git diff HEAD~5 -- .env apps/web/.env.local apps/web/.env.example` is empty.
