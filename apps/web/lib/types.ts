import type { components } from "../../../gapmap/shared/contracts/api";

export type Analysis = components["schemas"]["AnalysisResponse"];
export type Requirement = components["schemas"]["Requirement"];
export type Readiness = components["schemas"]["ReadinessResponse"];
export type Project = components["schemas"]["ProjectResponse"];
export type ProjectTask = components["schemas"]["ProjectTask"];
export type RunResult = components["schemas"]["RunResponse"];
export type Submission = components["schemas"]["SubmitResponse"];
export type EvidenceStatus = components["schemas"]["EvidenceStatus"];

export type AppState = {
  resumeText: string;
  jobText: string;
  analysis: Analysis | null;
  project: Project | null;
  queries: Record<string, string>;
  previews: Record<string, RunResult>;
  submissions: Record<string, Submission>;
  readiness: Readiness | null;
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
};