from uuid import uuid4

from fastapi.testclient import TestClient

from gapmap.apps.api.main import create_app
from gapmap.apps.api.services.demo_analysis import DemoAnalysisService
from gapmap.apps.api.services.interfaces import UnavailableProjectService


def create_demo_analysis(client: TestClient) -> dict:
    fixture = client.get("/api/demo/fixture").json()
    response = client.post("/api/analyze", json=fixture)
    assert response.status_code == 200
    return response.json()


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_fixture_analysis_recommendation_and_readiness(client: TestClient) -> None:
    analysis = create_demo_analysis(client)
    recommended = client.get(
        "/api/projects/recommended", params={"analysis_id": analysis["analysis_id"]}
    )
    assert recommended.status_code == 200
    assert recommended.json()["project_id"] == "revenue-debug-001"

    readiness = client.get("/api/readiness", params={"session_id": analysis["session_id"]})
    assert readiness.status_code == 200
    assert readiness.json()["project_total"] == {"earned": 0, "possible": 0}


def test_sql_project_service_is_installed_by_default(client: TestClient) -> None:
    project = client.get("/api/projects/revenue-debug-001")
    assert project.status_code == 200
    starter = {task["id"]: task["starter_sql"] for task in project.json()["tasks"]}
    analysis = create_demo_analysis(client)
    payload = {"session_id": analysis["session_id"], "task_id": "t3", "sql": starter["t3"]}

    run = client.post("/api/projects/revenue-debug-001/run", json=payload)
    assert run.status_code == 200 and run.json()["error"] is None
    submit = client.post("/api/projects/revenue-debug-001/submit", json=payload)
    assert submit.status_code == 200
    score = submit.json()["task_score"]
    readiness = client.get("/api/readiness", params={"session_id": analysis["session_id"]}).json()
    assert readiness["project_total"] == score


def test_project_placeholders_are_explicit() -> None:
    app = create_app(analysis_service=DemoAnalysisService(), project_service=UnavailableProjectService())
    with TestClient(app) as client:
        assert client.get("/api/projects/revenue-debug-001").json() == {
            "detail": "Project service is not installed."
        }
        analysis = create_demo_analysis(client)
        payload = {"session_id": analysis["session_id"], "task_id": "t1", "sql": "SELECT 1"}
        for suffix in ("run", "submit"):
            response = client.post(f"/api/projects/revenue-debug-001/{suffix}", json=payload)
            assert response.status_code == 501
            assert response.json() == {"detail": "Project service is not installed."}


def test_unknown_analysis_and_session_return_404(client: TestClient) -> None:
    response = client.get("/api/projects/recommended", params={"analysis_id": str(uuid4())})
    assert response.status_code == 404
    response = client.get("/api/readiness", params={"session_id": str(uuid4())})
    assert response.status_code == 404


def test_invalid_analysis_input_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/analyze", json={"resume_text": " ", "job_description": "SQL"}
    )
    assert response.status_code == 422
    response = client.post(
        "/api/analyze", json={"resume_text": "x", "job_description": "x" * 50_001}
    )
    assert response.status_code == 422


def test_non_demo_analysis_returns_sanitized_503(client: TestClient) -> None:
    response = client.post(
        "/api/analyze",
        json={"resume_text": "Python", "job_description": "A different posting"},
    )
    assert response.status_code == 503
    assert "Demo mode supports only the bundled posting" in response.json()["detail"]


def test_local_frontend_cors_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_demo_happy_path_has_traceable_initial_state(client: TestClient) -> None:
    fixture = client.get("/api/demo/fixture").json()
    analysis = client.post("/api/analyze", json=fixture).json()
    by_id = {item["id"]: item for item in analysis["requirements"]}
    assert by_id["req-sql"]["job_quote"] in fixture["job_description"]
    assert by_id["req-sql"]["evidence_status"] == "unverified"
    assert by_id["req-react"]["verification_capability"] == "not_assessable"
    assert by_id["req-docker"]["verification_capability"] == "not_assessable"
    assert analysis["recommended_project_id"] == "revenue-debug-001"
