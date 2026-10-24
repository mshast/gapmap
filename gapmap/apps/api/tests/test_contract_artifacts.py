import json
from pathlib import Path

from gapmap.apps.api.main import create_app


def test_openapi_snapshot_matches_application() -> None:
    expected = json.loads(Path("gapmap/shared/contracts/openapi.json").read_text())
    assert expected == create_app().openapi()


def test_typescript_contract_contains_core_operations() -> None:
    declarations = Path("gapmap/shared/contracts/api.d.ts").read_text()
    assert '"/api/analyze"' in declarations
    assert '"/api/readiness"' in declarations
    assert '"/api/projects/{project_id}/submit"' in declarations
