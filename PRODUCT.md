# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Students targeting software engineering internships.

## Product Purpose

GapMap helps a student understand how a resume matches a specific internship posting, test gaps that the resume does not demonstrate, and choose practical next steps based on the results.

Success means a student can move through the three-stage flow: resume and posting analysis, a focused work-sample assessment for uncovered skills, and a prioritized roadmap of suggestions.

## Positioning

GapMap connects job requirements to traceable evidence, then turns missing or unverified evidence into a job-relevant practice task and follow-up actions. It is not a hiring-probability predictor or a certification system.

## Operating Context

The primary use case is a short, self-guided web session during a hackathon demo or internship-preparation workflow. A student provides a resume as text or a text-based PDF and pastes one software internship posting, reviews evidence, completes SQL work-sample tasks when applicable, and checks the updated roadmap.

## Capabilities and Constraints

- Stage 1 extracts requirements from one posting and maps them to resume quotes.
- Stage 2 tests assessable gaps through a fixed, deterministic mini-project; the current project is an e-commerce SQL revenue-debugging exercise.
- Stage 3 prioritizes suggestions from requirement importance, evidence status, and competency coverage.
- Resume claims, project-tested evidence, and unavailable verification must remain distinct.
- Demo mode must be deterministic and complete quickly without external services.
- Uploaded documents are untrusted data; they must not control scoring, tools, or endpoints.
- Raw documents should not be retained beyond the session needs, and the product must not fabricate job-fit predictions or certifications.
- Sessions are currently in-memory and reset when the API restarts.

## Brand Commitments

The product name is GapMap. Product language should be direct, practical, and honest about what the evidence does and does not prove.

## Evidence on Hand

- Canonical demo resume: `demo/resume.txt`.
- Canonical demo posting: `demo/job-description.txt`.
- Demo walkthrough: `demo/walkthrough.md`.
- Existing frontend and API implement the analysis, SQL project, grading, and roadmap flow.
- No user testimonials, impact claims, or placement statistics are available; future work must not invent them.

## Product Principles

- Trace every conclusion to source text or measured project output.
- Turn an evidence gap into a concrete next action.
- Keep self-report, assessment, and unavailable verification visibly separate.
- Optimize the core path for a short, reliable hackathon demo.
- Treat privacy and adversarial input as product requirements, not afterthoughts.

## Accessibility & Inclusion

The web experience should remain keyboard-usable, responsive on a standard laptop, and clear to users who need explicit explanations of evidence status. A missing resume mention must never be presented as proof that a student lacks the skill.
