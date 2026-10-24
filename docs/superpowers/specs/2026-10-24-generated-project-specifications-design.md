# Generated Project Specifications Design

## Summary

GapMap will replace generic skill-template recommendations with concrete, posting-grounded project specifications. One separate, structured Groq request will generate up to four project specifications for the highest-priority project-eligible gaps in an analysis. Results will be cached with the analysis session so opening or revisiting project pages does not consume additional provider requests.

This is feasible within the stated Groq free-tier limits because normal use adds one request per analysis, not one request per project. The implementation cannot guarantee provider availability when the same API key is used elsewhere, but it will prevent GapMap from repeatedly spending quota for the same analysis.

## User Outcome

Each recommended project must answer the questions the current page leaves open:

- What product am I building?
- Who uses it, and what problem does it solve?
- What information goes in and what should come out?
- What behavior is required?
- What should I build first, second, and third?
- How do I know each milestone is complete?
- What tests and edge cases must I cover?
- What artifacts should I publish to demonstrate the target competency?
- Which exact job-posting requirement does the work demonstrate?

The result is a buildable project brief, not an instruction to invent a project.

## Scope

### Included

- Generate up to four specifications for the highest-priority gaps that can reasonably be demonstrated through a software project.
- Use one batched Groq call per analysis.
- Ground every specification in a stored requirement ID and exact job-posting quote.
- Store generated specifications in the existing in-memory analysis session.
- Return cached specifications for repeated requests.
- Validate all model output before storing or displaying it.
- Preserve the existing deterministic templates as an explicitly labeled fallback.
- Keep `revenue-debug-001` as the only automatically graded project.

### Excluded

- A separate provider call for each project.
- Automatic regeneration, background refresh, or polling.
- Executing or grading arbitrary generated projects.
- Sending the complete resume to project generation.
- Durable project storage across API restarts.
- Editing environment files or introducing another provider.

## Project Specification Contract

Each generated project contains:

```text
id                  Stable server-issued plan ID tied to the requirement
requirement_id      Existing analyzed requirement ID
title               Concrete product name, not a technology-only title
summary             Two or three sentences defining the user and problem
job_quote           Exact stored posting excerpt
skills              Canonical skills this project demonstrates
scenario            Realistic operating context and intended user
inputs              Bounded list of data or user inputs
outputs             Bounded list of observable outputs
constraints         Technical and product constraints
deliverables        Files, documentation, tests, and demo artifacts to publish
milestones          Three to five ordered milestones
source              "generated" or "fallback"
```

Each milestone contains:

```text
title               One concrete implementation outcome
work                 Two or three specific tasks
acceptance_criteria  Two to four observable completion checks
tests                At least one happy-path and one relevant failure/edge case
evidence             What the user can show to demonstrate the mapped gap
```

All fields have strict maximum lengths and list sizes. Unknown model fields are rejected.

## Gap Selection

The server selects gaps before calling Groq. The model does not choose priorities.

1. Start from the current readiness requirements so completed competencies are excluded.
2. Remove eligibility requirements such as degree, graduation date, work authorization, citizenship, visa, or sponsorship.
3. Sort by existing roadmap priority and original posting order.
4. Select at most four requirements.
5. Preserve each requirement ID, exact job quote, canonical skills, and requirement type.

If no project-eligible gaps remain, return an empty successful result and do not call Groq.

## Generation Request

The API exposes one analysis-scoped endpoint:

```http
POST /api/project-plans/generate
Content-Type: application/json

{
  "session_id": "...",
  "analysis_id": "..."
}
```

The endpoint verifies that the analysis belongs to the session, then returns either the cached plans or performs one batch generation. The response contains the plans, source, and a non-sensitive status message.

The Groq prompt receives only:

- target role;
- selected requirement IDs;
- requirement labels and types;
- exact job quotes;
- canonical skills; and
- output-schema instructions.

The full resume, resume quotes, interview answers, and other session data are omitted because they are unnecessary for project design.

Documents remain untrusted data. Posting excerpts are placed inside randomized delimiters, and the system prompt states that embedded instructions must be ignored.

## Rate-Limit Controls

The user-provided Groq allowance for the selected models is 30 requests per minute, 1,000 requests per day, 8,000 tokens per minute, and 200,000 tokens per day. GapMap will remain well below the request limit during normal single-user use:

- At most one successful generation request per analysis.
- At most four plans per request.
- No provider call on project-page navigation.
- No automatic regeneration.
- Concurrent requests for the same analysis share one in-flight generation operation.
- Completed results are cached before the endpoint responds.
- A `429` is never retried automatically. The API returns a sanitized temporary-unavailable status and, when supplied, a safe `Retry-After` value.
- Invalid structured output may be retried once, so the strict worst case is two provider requests for an analysis.

The request builder enforces a conservative token budget. Selected posting excerpts are already limited to 400 characters each. Prompt content is capped before sending, and `max_completion_tokens` is set so the combined request and completion remain below the 8,000-token-per-minute allowance. If the bounded request cannot fit, the server skips Groq and returns fallback specifications rather than truncating requirement quotes into misleading fragments.

No promise is made about quota consumed by other applications sharing the Groq key.

## Storage and Concurrency

The in-memory session record stores generated plans alongside the analysis. A paired `(session_id, analysis_id)` lookup is required for both reads and generation.

The session store provides three narrow operations:

- load cached plans for the paired IDs;
- mark or coordinate one in-flight generation for the paired IDs; and
- atomically store the validated result.

Two simultaneous requests for one analysis must not create two Groq calls. Requests for different analyses remain independent. Provider failures do not poison the cache; deterministic fallback plans may be returned for that response, while a later explicit user retry can attempt generation again.

## Validation and Grounding

Pydantic models reject unknown fields, excessive list sizes, missing milestones, empty acceptance criteria, and unsupported skill IDs.

After schema validation, deterministic checks enforce that:

- every returned `requirement_id` is one of the selected requirements;
- each requirement appears at most once;
- `job_quote` exactly matches the stored requirement quote;
- returned skills are a subset of the requirement's stored canonical skills;
- titles identify a product or workflow rather than only repeating a technology;
- there are three to five milestones;
- each milestone includes work, acceptance criteria, tests, and evidence; and
- no plan claims automatic grading unless its `runnable_project_id` is the existing SQL project.

Invalid plans are discarded individually. Missing plans are filled from the deterministic fallback so one malformed item does not erase otherwise valid results.

## Fallback Behavior

Fallback content remains available when:

- Groq is not configured;
- the token budget cannot safely fit;
- Groq returns `429` or another provider error;
- structured output remains invalid after one retry; or
- a generated item fails grounding checks.

Fallback plans are labeled `source: "fallback"`. They must still be more actionable than the current page: each supported skill family receives a concrete scenario, explicit inputs and outputs, three milestones, acceptance criteria, tests, and portfolio deliverables. The interface does not imply that fallback content was AI-generated.

## Frontend Flow

The readiness page initially renders available cached plans. If generated plans are missing, it offers one explicit `Generate tailored projects` action rather than generating invisibly on every page load. This keeps provider use understandable and prevents accidental requests while navigating.

During generation, the action is disabled and communicates that one set of plans is being created. On success, recommendation cards update from fallback to generated content. On rate limiting or provider failure, fallback cards remain usable and the user sees a concise retry message.

The project-detail page renders:

1. Project title, target role, and exact mapped posting quote.
2. Scenario and intended user.
3. Inputs, outputs, and constraints.
4. Required deliverables.
5. Ordered milestones, each with work, acceptance criteria, tests, and evidence.
6. A source label: `Tailored from this posting` or `Fallback project template`.
7. The existing graded-assessment action only for SQL plans mapped to `revenue-debug-001`.

Refreshing or reopening a generated plan uses stored session data and makes no Groq request. If browser state is missing or stale, the existing recovery link returns the user to the evidence map.

## Error Handling and Privacy

- Provider response bodies are never logged or returned.
- API keys remain server-side.
- Public errors contain no resume text, posting excerpts, prompt content, or generated content rejected by validation.
- `404` is returned for mismatched session and analysis IDs.
- `409` is reserved for generation already in progress when the request cannot join the existing operation.
- `429` or upstream unavailability produces a sanitized `503` response only when no fallback can be returned; otherwise the response succeeds with fallback plans and a warning.
- Generated specifications never change evidence status or readiness scoring.

## Testing

Backend tests cover:

- one Groq request generates multiple plans;
- repeated requests for an analysis use the cache;
- simultaneous requests do not duplicate provider calls;
- different analyses do not share cached plans;
- session and analysis ownership is enforced;
- eligibility requirements are excluded;
- current demonstrated competencies are excluded;
- prompt input omits resume and interview data;
- exact quotes and canonical skills are grounded;
- malformed, duplicate, or invented plans are rejected or replaced;
- a `429` is not retried;
- invalid structured output is retried at most once;
- token-budget overflow uses fallback without a provider call; and
- generated plans never alter competency evidence.

Frontend verification covers:

- the explicit generation action sends only one request while pending;
- successful plans replace fallback cards;
- provider failure leaves usable fallback cards;
- project detail renders scenario, inputs, outputs, constraints, deliverables, and milestone-specific checks;
- the source label is accurate; and
- revisiting a detail page does not call the generation endpoint.

The full Python suite, TypeScript check, lint, production build, and a browser walkthrough of generated and fallback flows must pass before completion.

## Acceptance Criteria

- A Python gap produces a specific product brief rather than `Build a Python workflow`.
- A user can begin implementation without inventing the problem, inputs, outputs, milestones, or success criteria.
- Four recommended plans require at most one normal Groq request.
- Reopening any generated plan consumes no provider request.
- Rate limiting never causes request loops or destroys fallback recommendations.
- Every displayed generated claim is traceable to an exact stored job-posting requirement.
- Only the existing SQL project is described as automatically graded.
