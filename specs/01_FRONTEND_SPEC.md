# GapMap — Part 1 of 4: Frontend and User Experience

## Codex assignment
Implement the web interface for the HackOHI/O GapMap MVP. Work primarily in `apps/web/`. Follow the shared contract in Part 4. Do **not** implement backend analysis or grading logic in the browser. If backend endpoints are not ready, use clearly labeled fixture data via an adapter that can be replaced with real API calls.

## Product goal
A student uploads or pastes a resume, pastes a specific software engineering internship posting, sees requirement-to-resume evidence, accepts a job-relevant mini-project, writes three SQL queries to debug an e-commerce revenue report, views deterministic test feedback, and sees evidence and next actions update.

## Recommended stack
- Next.js App Router, TypeScript (strict), Tailwind CSS.
- Monaco Editor (`@monaco-editor/react`) for SQL; load client-side only.
- `fetch` client through `lib/api.ts` with typed requests/results matching Part 4.
- Client state: React context or lightweight Zustand. No login/authentication.
- Accessible responsive layout. UI must work on a standard laptop screen at 1280×720.

## Screens and required behavior
1. **Start / Input (`/`)**
   - Resume PDF upload OR resume text paste (support both; server extracts text-based PDFs); max 5 MB; show extraction errors with paste fallback.
   - Job posting text area; clearly label text-only input; submit button disabled until input exists.
   - `Analyze` POSTs multipart/form or text to `/api/analyze` per Part 4. Show loading, failures, and retry.
   - Include `Load demo example` button loading the canonical fixture from `/api/demo/fixture` (fallback to checked-in fixture in mock mode).
2. **Readiness (`/readiness`)**
   - Show target role, 5–8 extracted job requirements, importance (required/preferred), supporting posting quote, resume quote if found, status: `resume_evidence`, `unverified`, or `project_demonstrated`/`partially_demonstrated` after results.
   - No “chance of being hired” scoring. Primary metric: `X of Y requirements with evidence`; segregate resume claims from project demonstration.
   - Clearly mark unsupported template coverage as `No verification project available` (e.g., React/Docker).
   - Select available SQL template when mapping intersects SQL competency; CTA `Start revenue debugging project`.
3. **Project workspace (`/project/[projectId]`)**
   - Title: `Investigate an E-commerce Revenue Bug`.
   - Scenario explanation and visible schema: `customers(id,name,region)`, `orders(id,customer_id,amount_cents,status,created_at)`, `refunds(id,order_id,amount_cents)`.
   - Three sequential tasks: join completed orders with regions; gross revenue by region excluding invalid statuses; net revenue by region accounting for refunds, including multiple refunds per order.
   - Monaco SQL editor per task with starter code; `Run preview` calls `/api/projects/{id}/run`, displays max 20 result rows/error. `Submit for evaluation` calls `/api/projects/{id}/submit`, shows partial tests, points and competency feedback.
   - Preserve draft queries across task navigation within the session. Allow resubmission.
   - Do not present preview as the hidden grading verdict.
4. **Results and roadmap (`/results`)**
   - Display actual test outcomes with task IDs and competency breakdown (joins 25, filtering 20, aggregation 25, refund/edge cases 30; 100 total), earned points and unmet cases.
   - Render statuses precisely: `unverified`, `partially_demonstrated`, `demonstrated_on_project`, `not_assessable`. No certifications.
   - Show a before/after evidence trail and prioritized next 2–3 actions pulled from `/api/readiness`.
   - Links back to project to retry failed tasks and readiness dashboard.

## UX rules
- Prioritize one coherent path over feature count. No interview, scraping, applications, sign-in, or arbitrary project creation.
- Distinguish **job requirement quote**, **resume claim**, and **tested competency** visually and semantically.
- Explain status: `not mentioned on resume` ≠ `does not know skill`.
- Every API-driven state must show skeleton/loading, error, empty state, and retry.
- No hardcoded '73% chance of getting hired' or LLM-derived pass labels.
- Usability demo should finish within 3 minutes using pre-loaded sample inputs and task solutions.

## File ownership
Own `apps/web/**`, including pages, components, styles, API client/types import. Coordinate shared API schema with Part 4; do not edit backend grading fixtures or Part 2/3 modules.

## Acceptance checks
- [ ] Sample resume/job -> readiness dashboard (via API or mock adapter).
- [ ] Every requirement has a source snippet or says evidence absent.
- [ ] SQL project shows three coherent tasks; run/submit handles success and failure.
- [ ] Submission updates task score, competency states, and roadmap on refresh.
- [ ] No unverifiable job-fit percentage; accessible keyboard-navigation and responsive layout.
- [ ] Frontend builds with `npm run build`, lint/typecheck pass.
