# GapMap Three-Minute Demo Walkthrough

This walkthrough separates the working integration foundation from the frontend, general analysis, and SQL grader work owned by Parts 1–3.

## 0:00–0:20 — Problem

Students often know that a role asks for skills they have not yet demonstrated, but a keyword match does not explain what evidence is missing. GapMap traces requirements to the posting and recommends a focused work sample instead of claiming a job-fit percentage.

## 0:20–0:45 — Inputs

Show `demo/resume.txt` and `demo/job-description.txt`. Call out that the resume includes Python project experience but no SQL claim. Explain that the current foundation uses this deterministic fixture; general AI analysis and PDF extraction arrive with Part 2.

## 0:45–1:05 — Traceable gaps

Submit the fixture to `POST /api/analyze`. Show the exact SQL, React, and Docker quotes from the posting. SQL begins `unverified`; React and Docker have `verification_capability: not_assessable` because the initial mini-project cannot test them.

## 1:05–1:35 — Recommended project

Show `GET /api/projects/recommended` returning `revenue-debug-001` because it assesses the required SQL skills. Until Part 3 integrates, project detail, run, and submit routes intentionally return `501 Project service is not installed.`

## 1:35–2:10 — Failing then passing SQL assessment

After Part 3 integration, run the incorrect T3 query that double-counts orders with multiple refunds, show safe public feedback, then run the corrected query. Do not record this segment until the real deterministic grader and hidden fixtures are connected.

## 2:10–2:35 — Evidence and roadmap

Show `GET /api/readiness`. The current foundation recomputes readiness from the latest successful task attempt, prevents retry scores from accumulating, requires all mapped assessable SQL subskills for full demonstration, and never transfers SQL evidence to React or Docker.

## 2:35–3:00 — Architecture and lesson

Show the FastAPI contract layer, replaceable analysis/project service interfaces, generated TypeScript declarations, and session store. Explain that stable contracts let the four workstreams proceed independently, while explicit capability gaps keep the demo honest.

Project results evidence narrow SQL competencies from this work sample; GapMap does not predict employability or job-placement odds.
