"""Check the complete running demo; start npm run demo first."""

import argparse
from pathlib import Path

import httpx

SOLUTIONS = Path(__file__).resolve().parents[1] / "demo/solutions"
PROJECT = "/api/projects/revenue-debug-001"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        def get(path, **kwargs):
            response = client.get(path, **kwargs)
            response.raise_for_status()
            return response.json()

        def post(path, payload):
            response = client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

        fixture = get("/api/demo/fixture")
        analysis = post("/api/analyze", fixture)
        assert analysis["analysis_mode"] == "demo", "Run npm run demo for deterministic verification."
        session_id = analysis["session_id"]
        assert next(r for r in analysis["requirements"] if r["id"] == "req-sql")["evidence_status"] == "unverified"
        assert get(PROJECT)["id"] == "revenue-debug-001"
        print("PASS: fixture, analysis, and project load through the frontend")

        def attempt(task_id, solution, action="submit"):
            return post(f"{PROJECT}/{action}", {"session_id": session_id, "task_id": task_id, "sql": (SOLUTIONS / solution).read_text()})

        preview = attempt("t1", "t1.sql", "run")
        assert preview["error"] is None and preview["rows"]
        for task_id in ("t1", "t2"):
            score = attempt(task_id, f"{task_id}.sql")["task_score"]
            assert score["earned"] == score["possible"]
        partial = get("/api/readiness", params={"session_id": session_id})
        assert next(r for r in partial["requirements"] if r["id"] == "req-sql")["evidence_status"] == "partially_demonstrated"
        print("PASS: real preview and initial tasks; outstanding tests remain partial")

        wrong = attempt("t3", "t3-naive.sql")
        assert wrong["task_score"]["earned"] < 40
        assert any(not feedback["passed"] and "several refunds" in feedback["label"] for feedback in wrong["public_test_feedback"])
        print("PASS: naive refund join fails the multiple-refund case")
        attempt("t3", "t3.sql")
        final = get("/api/readiness", params={"session_id": session_id})
        assert final["project_total"] == {"earned": 100, "possible": 100}
        assert next(r for r in final["requirements"] if r["id"] == "req-sql")["evidence_status"] == "demonstrated_on_project"
        assert all(r["evidence_status"] == "unverified" for r in final["requirements"] if r["id"] in {"req-react", "req-docker"})
        assert "req-sql" not in {item["requirement_id"] for item in final["roadmap"]}
        print("PASS: corrected query gives 100/100 and updates only relevant evidence and roadmap")


if __name__ == "__main__":
    main()
