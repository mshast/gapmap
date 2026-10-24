# Project Details and Groq Interviews Design

## Goal

Make every posting-grounded competency recommendation inspectable, and make the new mock interview feature work through the same Groq-backed configuration as analysis without weakening session isolation.

## Scope

- Keep `revenue-debug-001` as the only executable, automatically graded project.
- Keep deriving recommendation content deterministically from the analyzed requirement and its exact job-posting quote.
- Add a project-spec detail route for every recommendation. SQL recommendations retain a separate action into the existing graded assessment.
- Wire the existing interview module into the production FastAPI application.
- Select Groq for interviews when `GAPMAP_LLM_PROVIDER=groq`, using the existing Groq key and model variables already used by analysis.
- Reject interview starts unless the supplied analysis belongs to the supplied session.
- Do not edit environment files, add providers, build new graders, or let interview feedback alter competency evidence.

## Project Detail Flow

`plansForRequirements` remains the single frontend source for recommendation content. Each plan receives a stable URL derived from its plan ID. Recommendation cards on readiness and results become links to `/projects/[planId]` instead of leaving non-SQL plans inert.

The detail page resolves the plan from the analysis/readiness state already held by `AppStateProvider`. It shows:

- the targeted competency gap;
- the exact posting quote that motivated the recommendation;
- the intended deliverable;
- the existing ordered implementation milestones; and
- clear completion criteria derived from the deliverable and milestones.

If a plan has `runnableProjectId`, the detail page exposes a second action to load and open the existing graded SQL assessment. A missing analysis, stale plan ID, or refreshed in-memory session gets a clear recovery link back to analysis/readiness rather than silently substituting the SQL project.

## Interview Provider and API Wiring

The interview client will accept a provider endpoint as constructor data, matching the existing structured-analysis client. `client_from_env` will use the existing provider selector:

- `groq`: `GROQ_API_KEY`, the existing Groq model variable/default, and Groq's OpenAI-compatible chat-completions endpoint;
- `openai`: the existing OpenAI key/model and endpoint;
- explicit demo mode: the existing deterministic demo client.

The FastAPI factory will construct one session store, use it for both analysis state and `InterviewService`, and include the interview router. Tests may still inject an interview service so provider calls remain isolated.

No secret or provider response body is returned or logged. Provider failures remain the existing generic public error.

## Session Ownership

`InMemorySessionStore` will expose one narrow lookup that returns requirements only when both IDs identify the same stored analysis. `SessionStoreAnalysisSource` will use that lookup instead of independently checking one analysis ID and one session ID. Two valid IDs from different analyses must return not found.

## Testing

Focused tests will verify:

- Groq selects the Groq endpoint, key, and configured model;
- the real application exposes the interview start route;
- mismatched valid session and analysis IDs are rejected;
- each recommendation card links to its own detail route;
- a non-SQL project detail renders its posting-grounded content;
- a SQL project detail retains the graded-assessment action; and
- missing or stale plan state gives a recoverable empty state.

The default test configuration will include the interview test directory so these checks run in the ordinary suite. Existing API and frontend checks must remain green.

## Out of Scope

- Executable graders for Python, React, Docker, algorithms, or arbitrary generated projects.
- LLM-generated project specifications.
- Persistent storage across server or browser restarts.
- Interview-driven competency-score changes.
- Environment-file changes.

These limits keep the implementation honest: recommendations are posting-grounded project specifications, while only the existing SQL project is represented as automatically graded.
