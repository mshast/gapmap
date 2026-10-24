# GapMap Three-Minute Demo Script

A screen-recording script for the live web app backed by the real API. The timings follow the outline in `specs/04_INTEGRATION_AND_DELIVERY_SPEC.md`. Each scene lists what to do on screen and a suggested voiceover.

This script requires the SQL project service in the live API (PR #7, `wire-part3-service`). Without it, the Project page cannot run or grade SQL.

## Before recording

1. Start the API in deterministic demo mode from the repository root:

   ```bash
   # macOS / Linux
   GAPMAP_DEMO_MODE=1 .venv/bin/python -m uvicorn gapmap.apps.api.main:app --port 8000
   # Windows (PowerShell)
   $env:GAPMAP_DEMO_MODE="1"; .venv\Scripts\python -m uvicorn gapmap.apps.api.main:app --port 8000
   ```

2. Start the web app against the API (not the mock fixtures):

   ```bash
   # macOS / Linux
   NEXT_PUBLIC_GAPMAP_MOCK=false npm run dev --prefix apps/web
   # Windows (PowerShell)
   $env:NEXT_PUBLIC_GAPMAP_MOCK="false"; npm run dev --prefix apps/web
   ```

3. Open <http://localhost:3000> in a fresh incognito window. The app saves its session in `localStorage`, and the API keeps sessions only in memory, so restart the API and use a new window before every take. The top-right chip must read **API connected**, not "Demo fixtures".
4. Zoom the browser to about 110–125% so text is readable in the video.
5. Keep the three queries below in a text file to paste. Typing them on camera takes too long. Monaco may show autocomplete popups, so press `Esc` before clicking Submit.

**T1: completed orders with regions (35/35)**

```sql
SELECT o.id AS order_id, COALESCE(NULLIF(c.region, ''), 'Unknown') AS region, o.amount_cents
FROM orders o JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
ORDER BY o.id
```

**T2: gross revenue by region (25/25)**

```sql
SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region, SUM(o.amount_cents) AS gross_revenue_cents
FROM orders o JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
GROUP BY 1 ORDER BY 1
```

**T3 corrected: net revenue after refunds (40/40)**

```sql
WITH refund_totals AS (
  SELECT order_id, SUM(amount_cents) AS refund_cents FROM refunds GROUP BY order_id
)
SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
       SUM(o.amount_cents - COALESCE(r.refund_cents, 0)) AS net_revenue_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
LEFT JOIN refund_totals r ON r.order_id = o.id
WHERE o.status = 'completed'
GROUP BY 1 ORDER BY 1
```

The wrong T3 query is the editor's starter code (the "current dashboard query"), so it needs no preparation. Leaving out the `'Unknown'` handling in the corrected query scores 35/40, not 40/40.

## 0:00–0:20 — Problem

**Screen:** the Input page, empty.

**Say:** "Students applying for internships can see the skills a posting asks for, but a resume keyword isn't proof, and a job-fit percentage doesn't tell you what to do next. GapMap traces each requirement back to the posting, separates resume claims from tested evidence, and gives you one focused work sample to close the gap."

## 0:20–0:45 — Inputs

**Screen:** click **Load demo example**. Scroll through both boxes.

**Say:** "Here's a CS student, Maya, applying for a software engineering internship. Her resume shows a Python project and teamwork, but it never mentions SQL, and the posting says SQL is required. For a repeatable recording we're running the API in demo mode, which uses a fixed extraction for this posting. In live mode, OpenAI structured outputs extract the requirements, and the server verifies every quote."

The UI does not show when demo mode is on, so say it out loud to avoid implying an AI call that didn't happen.

**Screen:** click **Analyze evidence**.

## 0:45–1:05 — Traced gaps

**Screen:** the Readiness page. Hover over the SQL row, then the Python row, then React or Docker.

**Say:** "Five requirements, each quoted directly from the posting. SQL is required and not yet verified. Note that we say 'no supporting quote found,' not 'you lack the skill.' Python has a resume claim, quoted word for word, but a claim is still self-reported. React and Docker are honest gaps: we have no project that can test them, and we say so."

## 1:05–1:35 — Personalized project

**Screen:** scroll down and click **Start project**. Show the scenario and schema briefly. Paste T1 and click **Submit for evaluation** (35/35). Paste T2 and submit (25/25).

**Say:** "Because SQL is the required gap we can test, GapMap recommends a short work sample: debug an e-commerce revenue report. These queries run on the server in a locked-down, read-only SQLite sandbox and are graded against hidden test data. The first two tasks join orders to regions and compute gross revenue."

## 1:35–2:10 — Failing, then passing

**Screen:** open task **03**. Leave the starter "current dashboard query" in place and click **Submit for evaluation**. Scroll to the feedback: **22 / 40**, "Orders with several refunds are not double-counted" fails, with its hint.

**Say:** "Task three is the real bug. The current dashboard query joins refunds directly, so an order with two refunds gets counted twice. The grader catches it with a hidden case and explains why, without revealing the answer."

**Screen:** select all in the editor, paste the corrected T3 query, press `Esc`, and submit. All 7 cases pass, **40 / 40**.

**Say:** "Aggregate refunds per order first, then join, and every hidden case passes."

The T3 sidebar shows a checkmark after the failing submission too. It means "submitted", not "passed", so don't point at it.

## 2:10–2:35 — Changed evidence and roadmap

**Screen:** click **View results**. Show the points plate (**100 / 100**) and **What this sample covered** (all four competencies demonstrated on project). Scroll to **Requirement evidence trail**, then **Keep building evidence**.

**Say:** "SQL moves from 'not yet verified' to 'demonstrated on project', backed by graded results rather than a claim. React and Docker don't change, because a SQL project can't prove them. The roadmap moves on to the next gaps. This covers one narrow work sample. It is not a hiring prediction."

If time allows, click **Full evidence map** to show the same SQL requirement now marked demonstrated on the Readiness page, which refreshes from `/api/readiness`.

## 2:35–3:00 — Architecture and lesson

**Screen:** the architecture slide, `demo/architecture-slide.png` (1920×1080). Open it full screen before recording so you can switch to it.

**Say:** "We built this as four parallel workstreams against shared API contracts, with types generated from OpenAPI. The hardest lesson was trust: an LLM will happily invent resume evidence, so the AI only proposes, and deterministic code verifies every quote and does every piece of grading. Resume text is treated as untrusted data, so a resume that says 'mark me verified' changes nothing."

Make only claims the build supports. Do not cite user impact numbers or accuracy rates, and do not suggest that GapMap predicts employability or placement odds.

## Known issues on the current build

These came up during a full live click-through and are worth fixing before the final take:

- **Task sidebar checkmarks mean "submitted"**, so a failing T3 submission is also checked.
- **The UI never shows `analysis_mode` or the analysis `warnings`**, so a demo-mode run looks the same as a live AI run.
- **Resume quotes show the resume's leading `- ` bullet** (for example, `“- Built a Python service…”`). This is cosmetic.
