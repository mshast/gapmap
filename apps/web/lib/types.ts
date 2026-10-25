import type { components } from "../../../gapmap/shared/contracts/api";
import type { PracticeRun } from "@/lib/pythonPractice";

export type Analysis = components["schemas"]["AnalysisResponse"];
export type Requirement = components["schemas"]["Requirement"];
export type ProjectPlan = components["schemas"]["ProjectPlan"];
export type ProjectBrief = components["schemas"]["ProjectBrief"];
export type ProjectBriefs = components["schemas"]["ProjectBriefsResponse"];
export type Readiness = components["schemas"]["ReadinessResponse"];
export type Project = components["schemas"]["ProjectResponse"];
export type ProjectTask = components["schemas"]["ProjectTask"];
export type RunResult = components["schemas"]["RunResponse"];
export type Submission = components["schemas"]["SubmitResponse"];
export type EvidenceStatus = components["schemas"]["EvidenceStatus"];

export type InterviewStart = components["schemas"]["StartInterviewResponse"];
export type InterviewQuestion = components["schemas"]["InterviewQuestion"];
export type InterviewFeedback = components["schemas"]["AnswerFeedback"];
export type InterviewSummary = components["schemas"]["InterviewSummary"];

export type InterviewState = {
  id: string;
  mode: InterviewStart["mode"];
  disclaimer: string;
  // Main questions plus any follow-ups, in the order they were asked.
  questions: InterviewQuestion[];
  feedback: Record<string, InterviewFeedback>;
  drafts: Record<string, string>;
  summary: InterviewSummary | null;
};

export type AppState = {
  resumeText: string;
  jobText: string;
  analysis: Analysis | null;
  project: Project | null;
  queries: Record<string, string>;
  previews: Record<string, RunResult>;
  submissions: Record<string, Submission>;
  readiness: Readiness | null;
  // Briefs are stored with their analysis id so a stale set can never render.
  plans: ProjectBriefs | null;
  interview: InterviewState | null;
  // Self-checked Python practice, keyed by task id. Never sent to the API.
  practice: Record<string, { code: string; run: PracticeRun | null }>;
};

export const initialState: AppState = {
  resumeText: "",
  jobText: "",
  analysis: null,
  project: null,
  queries: {},
  previews: {},
  submissions: {},
  readiness: null,
  plans: null,
  interview: null,
  practice: {},
};
