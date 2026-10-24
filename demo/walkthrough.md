# GapMap: three-minute presentation rehearsal

## Start and verify

From the repository root, run `npm run demo`. It starts both servers with bundled analysis and real SQL execution. Open <http://localhost:3000>. Ctrl+C in that terminal stops both servers. If a port is occupied, stop the older server in its terminal first.

In a second terminal, run `npm run smoke`. Four PASS lines verify the complete flow through the frontend proxy, including a failing refund query, a corrected 100/100 result, and the updated roadmap. This creates its own session and does not change the browser's session.

Use the bundled example for the recording. No AI key is required, and the editor and PDF worker are served locally. Say that extraction is a labeled demo fixture; SQL execution and hidden-test grading are real. Live extraction is a separate provider-dependent capability.

Open these files in your editor before rehearsing:

- `demo/solutions/t1.sql`
- `demo/solutions/t2.sql`
- `demo/solutions/t3-naive.sql` (intentionally incorrect)
- `demo/solutions/t3.sql` (corrected)

Paste whole queries during the demo. Do not type SQL from scratch on stage.

## Click sequence

| Time | Show | Action / message |
| --- | --- | --- |
| 0:00–0:20 | Input screen | Explain the gap between a resume claim and evidence of doing the work. |
| 0:20–0:45 | Resume and posting | Click Load demo example, then Analyze evidence. Maya is a fictional student whose resume has Python project experience and no SQL claim. |
| 0:45–1:05 | Evidence map | Point to the SQL posting quote, SQL not yet verified, Python resume evidence, and React/Docker having no matching test. |
| 1:05–1:30 | SQL workspace | Start graded assessment. Paste and submit T1, then T2. They earn 35 and 25 points. SQL remains partial because T3 still contributes required tests. |
| 1:30–2:05 | Refund task | Select T3. Paste `t3-naive.sql`, submit, and point to the failed multiple-refund case. Paste `t3.sql` and resubmit for 40/40. |
| 2:05–2:30 | Results and evidence map | Click View results: 100/100, aggregation 25/25, refunds 30/30. SQL becomes demonstrated on this project. React and Docker stay unverified. Show the next actions. |
| 2:30–2:50 | Architecture / results | Explain that AI extracts text, source checks ground quotes, and deterministic tests grade SQL. Describe the early-verification bug and the regression test that fixed it. |
| 2:50–3:00 | Results | Close: GapMap gives a student a concrete way to build the next piece of evidence. |

## Before recording

- Run the smoke check and open the SQL editor once to warm the app.
- Click Reset session, then start the walkthrough from Input. This erases the browser's saved inputs and attempts.
- Rehearse twice with a timer. Aim to finish at 2:45, leaving room for clicks and pauses.
- Use a laptop viewport with legible text. Keep only the app and solution files ready.
- Capture a screen recording as a fallback. Screenshots from the browser test are under `output/playwright/`.
- Do not restart the API during the presentation: sessions are in memory. If it restarts, load the example and analyze again.

The speaking script, rubric evidence, research, and likely questions are in `demo/pitch.md`.
