# GapMap

GapMap turns traceable job requirements into a focused evidence-building roadmap. This repository currently contains the Part 4 integration foundation: stable FastAPI contracts, a deterministic demo analysis, replaceable service boundaries, in-memory session state, and generated TypeScript API declarations.

## Requirements

- Python 3.12
- Node.js 20 or newer
- npm

## Install

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
npm install
```

## Generate shared contracts

```bash
npm run contracts
```

This updates:

- `gapmap/shared/contracts/openapi.json`
- `gapmap/shared/contracts/api.d.ts`

Both files are checked in. The test suite fails when the OpenAPI snapshot no longer matches the application.

## Test

```bash
python -m pytest -q
```

## Run the API

```bash
uvicorn gapmap.apps.api.main:app --reload --port 8000
```

Then open:

- Health check: <http://localhost:8000/api/health>
- Interactive API documentation: <http://localhost:8000/docs>

The development frontend may call the API from `http://localhost:3000` or `http://127.0.0.1:3000`.

## Environment variables

None are required for the deterministic foundation. No external AI service runs in this phase.

## Implemented routes

- `GET /api/health`
- `GET /api/demo/fixture`
- `POST /api/analyze` for the bundled deterministic posting
- `GET /api/projects/recommended?analysis_id=...`
- `GET /api/readiness?session_id=...`

These contract-complete placeholders return `501 Project service is not installed.` until Part 3 is integrated:

- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/run`
- `POST /api/projects/{project_id}/submit`

General resume/job analysis and PDF parsing belong to Part 2 and are not implemented by the deterministic adapter.

## Demo

The canonical inputs and honest recording outline are under `demo/`. The fixture resume intentionally has no SQL claim. Job quotes in the response are exact substrings of the fixture posting.

The session store is single-process and in memory. **All analyses and assessment state reset whenever the API process restarts.** A durable store can replace it through the same integration boundary.

Project results evidence narrow competencies from one work sample. GapMap does not predict employability or job-placement odds.
