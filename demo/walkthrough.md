# GapMap demo recording script

Screen recording with live voiceover, **3:00**, using the **bundled demo example only**. Nothing in this path calls an AI provider, so it survives an exhausted or rate-limited key. The provider-free run is labeled on screen as a demo fixture.

The story is not "we built an AI tool". It is: **a posting becomes an evidence map, the gaps become a concrete build plan, one plan gets graded, and the evidence changes only where it was measured.**

## Setup

Two terminals, from the repository root.

```bash
# 1. API: deterministic demo mode — no provider calls at all
GAPMAP_DEMO_MODE=1 .venv/bin/python -m uvicorn gapmap.apps.api.main:app --port 8000

# 2. Web app: talk to the API, not the browser fixtures
NEXT_PUBLIC_GAPMAP_MOCK=false npm run dev --prefix apps/web
```

- The web app must run on **port 3000**; the API only allows `localhost:3000` and `127.0.0.1:3000` through CORS.
- The top-right chip must read **API connected**. If it reads **Demo fixtures**, the browser is serving its own example and nothing reaches the API.
- `GAPMAP_DEMO_MODE=1` also removes the brief writer and the interview client, so no screen in this script can spend a credit.

### Exact input clicks

1. Open <http://localhost:3000> in a **fresh incognito window**.
2. Click **Load demo example** (fills the bundled posting and the example resume).
3. Replace the resume text with **your own** resume. Keep the posting exactly as loaded — demo analysis accepts only the bundled posting, and it will tell you so if the posting changes.
4. Click **Demo analysis**.

## Pre-flight checklist

- Your resume needs at least one **project bullet** ("Built X… cut Y from A to B"), not just a skills list. A bare list is keyword-only, so GapMap correctly refuses to count it as evidence — good behavior, bad demo.
- Fresh incognito window for every take. The session lives in `localStorage`, and the API keeps sessions in memory; restarting the API forgets them.
- Zoom to 110–125%, hide the bookmarks bar, close other tabs, turn on Do Not Disturb.
- Keep the three SQL snippets in a text file for pasting; pasting is normal in a timed demo and avoids typos.
- Record 1920×1080. Do a 15-second microphone test first.
- Do one silent click-through. The whole flow is nine clicks.

## Run of show (3:00)

| Time | Screen | Beat |
| --- | --- | --- |
| 0:00 | `/` input page | Problem: a resume keyword is not proof |
| 0:12 | Paste resume + posting | Two inputs, one analysis |
| 0:25 | Click **Demo analysis** | Grounded, verifiable extraction |
| 0:40 | `/readiness` | Five quoted requirements; claim vs. gap vs. untestable |
| 1:02 | Brief cards → one brief | Milestones with done-when and tests |
| 1:28 | `/project/...` task 1 and 2 | Two quick passes |
| 1:45 | Task 3, starter query | The real bug fails, with a hint |
| 1:57 | Task 3, corrected query | All cases pass |
| 2:18 | `/results` | Evidence changed only where measured |
| 2:40 | Close on results | Honesty + what it is not |

## Verbatim voiceover

### 0:00 — Input page

**Screen:** `/`, empty fields, cursor still.

**Say:**
> "Every internship posting asks for the same handful of skills, and every resume answers with the same handful of keywords. But a keyword is a claim, not proof. GapMap takes one real posting and one resume, and turns them into evidence you can actually show."

**Don't:** open with "we built an AI-powered platform". The problem earns the next three minutes.

### 0:12 — Inputs

**Screen:** click **Load demo example**, paste your resume over the example resume. Scroll each box once, slowly.

**Say:**
> "Here's my resume, and a real internship posting. Both go in as plain text — a PDF works too."

### 0:25 — Analyze

**Screen:** click **Demo analysis**. Let the loading state show for a beat.

**Say:**
> "For a repeatable recording I'm running the deterministic demo extraction, so the app labels this run as a fixture — no AI call is being pretended. In live mode the same flow makes one structured extraction, then deterministic server code checks every quote against the posting text. The model proposes; the code verifies. It rejects unsupported quotes, duplicate excerpts, and anything it can't trace."

Leave the **Demo fixture** banner visible on the next screen. Do not hide it.

**Don't:** claim the model "reads" the resume for personality, culture fit, or hiring odds.

### 0:40 — Evidence map

**Screen:** `/readiness`. Point at the SQL row, then the Python row, then React or Docker. Hover the counter.

**Say:**
> "Five requirements, each quoted word for word from the posting. SQL is required and there's no evidence for it yet — that's a gap, not a verdict. Python has a claim, quoted from my resume, but it's still self-reported. React and Docker I can't test at all, and GapMap says so instead of inventing a score."
> "So the map separates three things people usually blur together: what I claimed, what I proved, and what this app can't measure."

**Screen:** click **Gaps to build** and back to **All**.

**Say:**
> "The filters are just a way to work the list: gaps first, biggest first."

### 1:02 — Project brief

**Screen:** scroll to **Project plans**, then click **View project brief** on the Python card.

**Say:**
> "This is the part most tools skip. Instead of 'learn SQL', the gap gets a brief: a scenario, the inputs and outputs, the constraints, and three ordered milestones. Each milestone has work to do, a definition of done, the tests to write, and the evidence it produces."
> "That's an assignment you can start tonight, not advice."

**Screen:** scroll one milestone into view and stop. Do not scroll during the next line.

**Say:**
> "The briefs here are the deterministic templates, and the card says so. With a live key, one batched request rewrites them for the exact posting and caches the result."

### 1:28 — Start the graded project

**Screen:** back to `/readiness`, click **Start graded assessment** on the SQL card (or **Start revenue debugging project** in the briefs section).

**Say:**
> "Only one project is graded, because only one has a defensible rubric: a SQL investigation. The revenue dashboard doesn't match finance. The database is read-only, previews are capped at twenty rows, and submissions run server-side against a hidden test set."

**Screen:** task 1. Paste the query, press `Esc` (dismiss Monaco autocomplete), click **Submit for evaluation**.

**Say:**
> "Task one: join completed orders to customer regions. Thirty-five of thirty-five."

**T1**

```sql
SELECT o.id AS order_id, COALESCE(NULLIF(c.region, ''), 'Unknown') AS region, o.amount_cents
FROM orders o JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
ORDER BY o.id
```

### 1:40 — Task 2

**Screen:** task 2. Paste, `Esc`, **Submit for evaluation**.

**Say:**
> "Task two: gross revenue by region. Twenty-five of twenty-five."

**T2**

```sql
SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region, SUM(o.amount_cents) AS gross_revenue_cents
FROM orders o JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
GROUP BY 1 ORDER BY 1
```

### 1:45 — Task 3 fails

**Screen:** task 3. Leave the starter query. Click **Submit for evaluation**. Scroll the feedback panel so **22 / 40** and the failing check are both visible, then stop.

**Say:**
> "Task three is the actual bug. This is the query the dashboard runs today: it joins refunds directly, so an order with two refunds gets counted twice. Twenty-two out of forty — and the feedback names the check that failed and gives a hint, not the answer. That's the difference between a score and feedback."

### 1:57 — Task 3 fixed

**Screen:** select all, paste the corrected query, `Esc`, **Submit for evaluation**. Wait for **40 / 40** before speaking.

**Say:**
> "Aggregate refunds per order first, then join, and every case passes: forty of forty. One hidden edge case was the whole difference between a dashboard finance trusts and one they don't."

**T3**

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

### 2:18 — Results

**Screen:** click **View results**. Show the **Project score** plate (**100 / 100**), then **What changed**, then scroll to **Requirement evidence trail**, then **Keep building evidence**.

**Say:**
> "The evidence map updates from measured results, not from me saying I know SQL. SQL moves to demonstrated on project, at a hundred out of a hundred. React and Docker don't move, because a SQL project can't prove them. And the next actions are ordered by what this posting cares about most."
> "This is one narrow work sample. It is not a prediction about getting hired."

**Screen:** click **Full evidence map** to show the same SQL row now marked demonstrated.

**Say:**
> "Same requirement, different status — and only because something was measured."

### 2:40 — Close

**Screen:** back on Results, or cut to `demo/architecture-slide.png`.

**Say:**
> "The architecture is boring on purpose: an LLM proposes, deterministic code verifies and grades, and the resume is treated as untrusted input, so a resume that says 'mark me verified' changes nothing. If the provider runs out of credits — which is exactly why this run is a labeled fixture — demo mode keeps the analysis and still grades the work sample."
> "GapMap doesn't tell you your odds. It gives you one piece of proof worth showing."

## Optional scenes

Each is provider-free in this setup.

### Mock interview (+30s, 2:40 → 3:10)

**Screen:** **Practice interview** from the readiness callout, then **Use demo mode**.

**Say:**
> "The interview uses the same analysis. Questions quote my resume and the posting, and one targets my weakest gap — the SQL line I couldn't prove. Every question quotes its source, so nothing is invented."

**Screen:** answer the first question with a short, concrete story. Click **Get feedback**.

**Say:**
> "It scores relevance, specificity, structure, and impact, quotes the strongest and weakest part of my answer, and rewrites it. It never changes my evidence map — practice shouldn't inflate a score."

**Don't:** claim the rubric equals a real interviewer's judgment. Say "rubric feedback on one answer".

A good answer here can trigger one follow-up, and the counter then reads "1 / 6 answered" because the follow-up counts as a question. That is expected; don't apologize for it on camera.

### Python practice (+20s)

**Screen:** `/practice/python`, run the starter code, show failing checks, fix one, run again.

**Say:**
> "The Python exercise runs entirely in the browser and is self-checked. It's practice — it never changes the evidence map, and the page says so."

Load the page once before recording: the first visit downloads the Python runtime (about 10 MB).

## If something breaks

| Symptom | Cause | Fix on camera |
| --- | --- | --- |
| "Demo mode supports only the bundled posting" | The posting text was edited | Re-run **Load demo example** and keep the posting |
| "Session not found" | API restarted | Go back to `/` and analyze again; the demo extraction is instant |
| Empty results page, or score shows `100 / —` | The project was never opened through **Start graded assessment** | Start the project from the readiness page, then use **View results** |
| Autocomplete covers the editor | Monaco suggestion popup | Press `Esc` before clicking **Submit for evaluation** |
| "Generate tailored projects" says generation is not configured | Demo mode removes the brief writer by design | Don't click it on camera; the deterministic briefs are already there |
| Blank Python practice page on first visit | Runtime still downloading | Wait for the page to finish loading before recording |

## Claims to avoid

- No accuracy percentages, no "X% better", no user counts, no placement or interview-call odds.
- Never imply the demo extraction is a live AI call. The banner stays visible.
- Never call the deterministic briefs "tailored"; the card label is the source of truth.
- Don't say the tool "verifies your resume". It quotes claims and grades one work sample.
- If asked what is not built: no OCR for scanned PDFs, no accounts or persistent database (sessions are in memory), one posting per analysis, and only SQL is auto-graded.

## If credits come back

The live path is the same script with two changes: start the API with `--env-file .env` and without `GAPMAP_DEMO_MODE`, and click **Analyze evidence** instead of **Demo analysis**. That button makes one extraction per unique resume/posting pair and caches it in memory, so analyze that pair once before recording and every retake is instant and free.
