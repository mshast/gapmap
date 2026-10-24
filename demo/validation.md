# Demo validation — October 24, 2026

The presentation path was checked against the real local API and frontend after the fixes in this change.

| Check | Result |
| --- | --- |
| `npm test` | 252 passed; includes API, project, and interview-module tests. One dependency deprecation warning. |
| Frontend TypeScript | Passed. |
| Frontend ESLint | Passed. Generated assets and test build output are excluded. |
| API-connected production build | Passed with `NEXT_PUBLIC_GAPMAP_MOCK=false`. |
| Playwright Chromium | 2 passed. The full journey blocked external browser requests and observed none. |
| `npm run demo` then `npm run smoke` | Four PASS lines through the frontend proxy, including partial evidence, naive-refund failure, corrected 100/100, and updated roadmap. |
| Duplicate launcher | Clear occupied-port message; no duplicate servers started. |
| Ctrl+C on launcher | Both child servers shut down; launcher exited successfully. |
| `git diff --check` | Passed. |

## Regression corrected

Before the fix, passing T1 reported filtering as fully demonstrated at 10/10, even though T2 contained another ten designated points. Passing T1 and T2 could also mark generic SQL demonstrated before T3's aggregation tests were attempted.

Readiness now uses the complete per-competency task allocation. After T1, filtering is 10/20 and partial. After T1 and T2, aggregation is 15/25 and partial. Full demonstration requires all designated task contributions. The regression test exercises real grading through the API.

The browser test also checks that a later failed T3 attempt replaces a passing attempt, downgrades evidence, and appears correctly on the evidence map. Reset session clears saved browser inputs and persists that cleared state after reload.

## Presentation assets

- `output/playwright/evidence-before.png`
- `output/playwright/assessment-failed.png`
- `output/playwright/evidence-after.png`
- `output/playwright/evidence-trail.png`

These are screenshots of the working prototype. They are not testimonials or measured user outcomes.

## Scope

The demonstration uses labeled fixture extraction with real query execution and hidden-test grading. Hosted-provider and local-model extraction were not exercised against a live model in this check. There are no external user-validation results yet. State remains in one API process, and the assessment covers one curated SQL project.

Playwright's browser was installed under temporary storage for this validation. To run browser tests on another machine, follow the browser installation command in the README first.
