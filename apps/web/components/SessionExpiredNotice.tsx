"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle, RotateCcw, TriangleAlert } from "lucide-react";
import { useAppState } from "@/components/AppStateProvider";
import { analyze } from "@/lib/api";

// The API keeps sessions in memory, so a restart (including --reload) forgets
// them while this browser still holds the old ids.
export const isSessionExpired = (message: string) => /^(?:session|analysis|interview) not found/i.test(message);

export function SessionExpiredNotice() {
  const { state, setState } = useAppState();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canRerun = Boolean(state.resumeText.trim() && state.jobText.trim());

  async function rerun() {
    setBusy(true); setError("");
    try {
      const result = await analyze(state.resumeText, state.jobText);
      // Keep SQL drafts and practice code; everything tied to the old session is reset.
      setState((current) => ({ ...current, analysis: result, project: null, readiness: null, previews: {}, submissions: {}, interview: null }));
      router.push("/readiness");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The analysis could not run. Try again.");
    } finally { setBusy(false); }
  }

  return (
    <div className="form-error session-expired" role="alert">
      <TriangleAlert size={16} />
      <span><b>This session expired.</b> The API restarted, and it keeps sessions only in memory. {canRerun ? "Re-run the analysis with the same resume and posting to continue." : "Start again from the input page."}{error && <><br />{error}</>}</span>
      {canRerun && <button className="button button-outline button-small" type="button" onClick={rerun} disabled={busy}>{busy ? <><LoaderCircle className="spin" size={14} /> Analyzing</> : <><RotateCcw size={14} /> Re-run analysis</>}</button>}
    </div>
  );
}
