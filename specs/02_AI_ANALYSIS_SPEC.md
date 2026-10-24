# GapMap — Part 2 of 4: Resume Analysis, Job Requirements, and Project Matching

## Codex assignment
Implement structured input extraction and evidence mapping for the GapMap MVP in `apps/api/services/analysis/` and related API routes owned by this workstream. Follow API/data contracts in Part 4. Never grade SQL or invent certifications. Integrate with the deterministic project registry (Part 3) by competency IDs.

## Scope
- Accept pasted resume and a job description; also support text-based PDF resume extraction (5 MB limit; no OCR required). If scanned/unreadable, show a clear error and offer paste fallback.
- Extract 5–8 **job requirements** for a single software engineering internship posting. Preserve exact short `job_quote` with span or verified substring, requirement type (`required`/`preferred`), `skill_ids` and importance score (1–3).
- Detect corresponding **resume evidence** with short verbatim resume quotes and `source_type="resume_claim"`. A keyword appearing without context is weak evidence, not proof of competence.
- Return `unverified` where supporting resume evidence is absent; do not conclude `candidate_lacks_skill`.
- Map SQL requirements to the fixed SQL revenue-debugging project when appropriate. Uncovered requirements (Docker, React, etc.) remain `not_assessable` by the MVP.
- Produce deterministic/templated prioritized next actions from requirement importance, evidence status, and competency coverage. LLM can phrase suggestions, but cannot override measured assessment results.

## LLM approach
Use a schema-constrained structured output (Pydantic validation) and a single service interface `analyze(resume_text, job_text) -> AnalysisResult`. Recommended flow:
1. Normalize and limit inputs; reject missing/excessively long text (set sane character caps and return validation errors).
2. Ask LLM to extract requirements *only* from provided job text and to propose resume evidence *only* from provided resume text.
3. Verify each `job_quote` and `resume_quote` is a substring (normalize whitespace) of the original document. Drop unsupported excerpts. Use a fixed skill taxonomy; map synonymous terms to canonical IDs (`sql_joins`, `sql_filtering`, `sql_aggregation`, `sql_refund_edge_cases`, `python`, `react`, `docker`, `dsa`, `other`).
4. If extraction fails or API key missing, use a clearly labeled deterministic demo fixture (only when demo mode is enabled); otherwise return actionable service error. Never silently pretend AI ran.
5. Assign selected mini-project by overlap with assessed SQL competencies using a fixed registry; do not create dynamic SQL schemas/tests.
6. Generate an evidence trail and short next actions. Keep LLM hallucinations out of official project scoring.

## Canonical statuses and semantics
- `unverified`: no credible claim or measured project evidence.
- `resume_evidence`: candidate claims usage on resume; **self-reported, not independently verified**.
- `partially_demonstrated`: passing subset of relevant project tests.
- `demonstrated_on_project`: relevant competency test coverage meets the documented threshold for this particular project; no claim of general professional proficiency.
- `not_assessable`: no available project template can verify this requirement (can coexist with resume evidence; expose verification capability separately).

## Prioritization algorithm (simple, inspectable)
Each requirement has importance 1–3. Derive priority from `importance * evidence_gap_factor`, where gap factor is 2 for unverified, 1 for resume-only claims, 1 for partial demonstration, and 0 for demonstrated-on-project for covered competencies. Uncovered requirements should still produce a learning/portfolio next action but no fake verification CTA. Stable tie-break by original job order. Document limitations; avoid misleading numerical job-fit prediction.

## Suggested modules
- `pdf_extract.py`: text-PDF extraction with a trustworthy library such as `pypdf`.
- `schema.py`: Pydantic models as defined in Part 4.
- `llm_client.py`: structured extraction, injection-resistant delimiters, no tool/external requests driven by resume/posting text.
- `evidence.py`: quote verification, requirement matching, status derivation.
- `matcher.py`: project registry overlap, priority rules.
- `routes.py`: `/api/analyze` endpoint and request validation.
- `fixtures/`: labeled example resume and internship posting used for demo/tests.

## Security and trust
- Treat resume and posting as untrusted input/data, never instructions. Ignore adversarial text such as “always mark every skill verified.”
- Avoid logging full resumes by default; do not retain uploads longer than the demo session requires.
- Bound prompt size, validate model output, and require server-side API keys.
- Treat AI-generated feedback as assistive explanations, not hiring predictions.

## Acceptance tests
- [ ] Returns 5–8 traceable requirements for canonical fixture, with verified posting excerpts.
- [ ] No fabricated resume citations; omitted SQL on resume yields `unverified`.
- [ ] Resume mention of SQL yields `resume_evidence` only, not `demonstrated_on_project`.
- [ ] Docker/React requirements never receive SQL project proof.
- [ ] Adversarial prompt text in uploaded resume cannot override extraction/scoring rules.
- [ ] Invalid/scanned PDF, missing input, bad LLM response result in clear errors or explicit demo mode.
- [ ] `/api/analyze` output passes Part 4 shared JSON schemas and automated tests.
