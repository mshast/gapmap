// Self-checked Python practice. Code runs only in the visitor's browser (Pyodide in a
// Web Worker), so results are practice feedback, never verified evidence.

export type PracticeCase = { label: string; expr: string; expected?: string; raises?: string };
export type PracticeTask = { id: string; title: string; instructions: string; starter: string; cases: PracticeCase[] };
export type CaseResult = { label: string; passed: boolean; message: string };
export type PracticeRun = { error: string | null; results: CaseResult[] };

const sampleEvents = `[
    {"title": "Resume Workshop", "date": "2026-01-05", "attendees": 18},
    {"title": "resume workshop ", "date": "2026-01-05", "attendees": 18},
    {"title": "Resume Workshop", "date": "2026-01-12", "attendees": 22},
]`;

export const pythonPractice = {
  id: "python-events-001",
  title: "Clean Up Campus Event Data",
  scenario:
    "The student center exports event data by hand, and the weekly attendance report keeps coming out wrong. " +
    "Write three small functions that parse durations, remove duplicate rows, and total attendance by week.",
  tasks: [
    {
      id: "p1",
      title: "Parse event durations",
      instructions:
        'Return the number of minutes in strings like "1h 30m", "45m", or "2h". Ignore case and surrounding ' +
        'spaces. Raise ValueError for anything else, including an empty string.',
      starter: `def parse_duration(text: str) -> int:
    """Return minutes for strings like "1h 30m", "45m", or "2h"."""
    raise NotImplementedError
`,
      cases: [
        { label: "Hours and minutes", expr: 'parse_duration("1h 30m")', expected: "90" },
        { label: "Minutes only", expr: 'parse_duration("45m")', expected: "45" },
        { label: "Hours only", expr: 'parse_duration("2h")', expected: "120" },
        { label: "Case and spacing", expr: 'parse_duration("  1H 5M ")', expected: "65" },
        { label: "Rejects free text", expr: 'parse_duration("soon")', raises: "ValueError" },
        { label: "Rejects an empty string", expr: 'parse_duration("")', raises: "ValueError" },
      ],
    },
    {
      id: "p2",
      title: "Remove duplicate events",
      instructions:
        "Return the events without duplicates. Two events are duplicates when their titles match ignoring case " +
        "and surrounding spaces, and their dates match. Keep the first copy, keep the original order, and do " +
        "not modify the input list.",
      starter: `def dedupe_events(events: list[dict]) -> list[dict]:
    """Drop repeated events, keeping the first copy of each."""
    raise NotImplementedError
`,
      cases: [
        { label: "Drops a case-insensitive repeat", expr: `len(dedupe_events(${sampleEvents}))`, expected: "2" },
        { label: "Keeps the first copy", expr: `dedupe_events(${sampleEvents})[0]["title"]`, expected: '"Resume Workshop"' },
        { label: "Same title on another date is kept", expr: `[e["date"] for e in dedupe_events(${sampleEvents})]`, expected: '["2026-01-05", "2026-01-12"]' },
        { label: "Empty input", expr: "dedupe_events([])", expected: "[]" },
        { label: "Input list is unchanged", expr: `(lambda events: (dedupe_events(events), len(events))[1])(${sampleEvents})`, expected: "3" },
      ],
    },
    {
      id: "p3",
      title: "Total attendance by week",
      instructions:
        'Return a dict from ISO week ("2026-W02") to total attendees, with keys in ascending order. Skip events ' +
        "whose attendees value is None. Use the ISO calendar, so early January can belong to the previous year's week 53.",
      starter: `from datetime import date


def weekly_attendance(events: list[dict]) -> dict[str, int]:
    """Total attendees per ISO week, keyed like "2026-W02"."""
    raise NotImplementedError
`,
      cases: [
        { label: "Sums one week", expr: 'weekly_attendance([{"date": "2026-01-05", "attendees": 10}, {"date": "2026-01-07", "attendees": 5}])', expected: '{"2026-W02": 15}' },
        { label: "Splits weeks", expr: 'weekly_attendance([{"date": "2026-01-04", "attendees": 3}, {"date": "2026-01-05", "attendees": 4}])', expected: '{"2026-W01": 3, "2026-W02": 4}' },
        { label: "Skips missing counts", expr: 'weekly_attendance([{"date": "2026-01-05", "attendees": None}, {"date": "2026-01-06", "attendees": 7}])', expected: '{"2026-W02": 7}' },
        { label: "ISO year boundary", expr: 'weekly_attendance([{"date": "2027-01-01", "attendees": 9}])', expected: '{"2026-W53": 9}' },
        { label: "Keys in ascending order", expr: 'list(weekly_attendance([{"date": "2026-03-02", "attendees": 1}, {"date": "2026-01-05", "attendees": 2}]))', expected: '["2026-W02", "2026-W10"]' },
      ],
    },
  ] satisfies PracticeTask[],
};

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const RUN_TIMEOUT_MS = 5000;

// Runs the solution in a fresh namespace, then each case in a copy of it.
export const PYTHON_RUNNER = `
import json

def _gapmap_run(user_code, cases):
    namespace = {"__name__": "solution"}
    try:
        exec(compile(user_code, "solution.py", "exec"), namespace)
    except Exception as error:
        return json.dumps({"error": f"{type(error).__name__}: {error}", "results": []})
    results = []
    for case in cases:
        env = dict(namespace)
        try:
            if case.get("raises"):
                try:
                    eval(case["expr"], env)
                except Exception as error:
                    raised = type(error).__name__
                    ok = raised == case["raises"]
                    message = "" if ok else f"raised {raised}, expected {case['raises']}"
                else:
                    ok, message = False, f"returned without raising {case['raises']}"
            else:
                actual = eval(case["expr"], env)
                expected = eval(case["expected"], {})
                ok = (actual == expected and list(actual) == list(expected)) if isinstance(expected, dict) else actual == expected
                message = "" if ok else f"returned {actual!r}, expected {expected!r}"
        except Exception as error:
            ok, message = False, f"{type(error).__name__}: {error}"
        results.append({"label": case["label"], "passed": ok, "message": message[:300]})
    return json.dumps({"error": None, "results": results})
`;

const workerSource = `
importScripts("${PYODIDE_URL}pyodide.js");
const ready = loadPyodide({ indexURL: "${PYODIDE_URL}" }).then((pyodide) => {
  pyodide.runPython(${JSON.stringify(PYTHON_RUNNER)});
  return pyodide;
});
ready.then(() => self.postMessage({ type: "ready" }), () => self.postMessage({ type: "load-error" }));
self.onmessage = async (event) => {
  const { id, code, cases } = event.data;
  try {
    const pyodide = await ready;
    const run = pyodide.globals.get("_gapmap_run");
    const output = run(code, pyodide.toPy(cases));
    run.destroy();
    self.postMessage({ type: "result", id, output });
  } catch (error) {
    self.postMessage({ type: "result", id, output: JSON.stringify({ error: String(error), results: [] }) });
  }
};
`;

let worker: Worker | null = null;
let ready: Promise<void> | null = null;
let nextId = 0;

function startWorker() {
  const url = URL.createObjectURL(new Blob([workerSource], { type: "text/javascript" }));
  const created = new Worker(url);
  worker = created;
  ready = new Promise((resolve, reject) => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type !== "ready" && event.data?.type !== "load-error") return;
      created.removeEventListener("message", onMessage);
      if (event.data.type === "ready") resolve();
      else reject(new Error("Python could not load. Check your connection and try again."));
    };
    created.addEventListener("message", onMessage);
    created.addEventListener("error", () => reject(new Error("Python could not load. Check your connection and try again.")));
  });
  ready.catch(() => { worker = null; });
}

/** Load Python ahead of the first run; safe to call repeatedly. */
export function preloadPython(): Promise<void> {
  if (!worker || !ready) startWorker();
  return ready!;
}

export async function runPractice(code: string, cases: PracticeCase[]): Promise<PracticeRun> {
  await preloadPython();
  const active = worker!;
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      // A runaway loop cannot be interrupted, so replace the worker.
      active.terminate();
      worker = null;
      active.removeEventListener("message", onMessage);
      reject(new Error(`Your code ran for more than ${RUN_TIMEOUT_MS / 1000} seconds and was stopped. Check for an infinite loop.`));
    }, RUN_TIMEOUT_MS);
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type !== "result" || event.data.id !== id) return;
      window.clearTimeout(timer);
      active.removeEventListener("message", onMessage);
      resolve(JSON.parse(event.data.output) as PracticeRun);
    };
    active.addEventListener("message", onMessage);
    active.postMessage({ id, code, cases });
  });
}
