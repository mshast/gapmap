import type { EvidenceStatus } from "@/lib/types";

const labels: Record<EvidenceStatus, string> = {
  unverified: "Not yet verified",
  resume_evidence: "Resume evidence",
  partially_demonstrated: "Partially demonstrated",
  demonstrated_on_project: "Demonstrated on project",
};

export function StatusPill({ status }: { status: EvidenceStatus }) {
  return <span className={`status-pill status-${status}`}>{labels[status]}</span>;
}