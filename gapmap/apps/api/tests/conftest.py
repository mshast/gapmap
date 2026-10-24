import pytest
from importlib.resources import files
from fastapi.testclient import TestClient

from gapmap.apps.api.main import create_app
from gapmap.apps.api.services.demo_analysis import DemoAnalysisService
from gapmap.apps.api.services.analysis.schema import ExtractionResult


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app(analysis_service=DemoAnalysisService())) as test_client:
        yield test_client


@pytest.fixture
def extraction_result() -> ExtractionResult:
    path = files("gapmap.apps.api.services.analysis.fixtures").joinpath("demo_extraction.json")
    return ExtractionResult.model_validate_json(path.read_text(encoding="utf-8"))
