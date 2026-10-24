import pytest
from pydantic import ValidationError

from gapmap.apps.api.contracts import (
    AnalyzeRequest,
    EvidenceStatus,
    Requirement,
    RequirementType,
    VerificationCapability,
)


def test_analyze_request_strips_text_and_rejects_empty_values() -> None:
    request = AnalyzeRequest(resume_text="  Python projects  ", job_description="  SQL required  ")
    assert request.resume_text == "Python projects"
    with pytest.raises(ValidationError):
        AnalyzeRequest(resume_text="   ", job_description="SQL required")


def test_requirement_serializes_canonical_enum_values() -> None:
    requirement = Requirement(
        id="req-sql",
        label="SQL relational querying",
        job_quote="Experience with SQL databases",
        importance=3,
        requirement_type=RequirementType.REQUIRED,
        skill_ids=["sql_joins", "sql_filtering", "sql_aggregation"],
        resume_quotes=[],
        evidence_status=EvidenceStatus.UNVERIFIED,
        verification_capability=VerificationCapability.AVAILABLE,
    )
    assert requirement.model_dump(mode="json")["evidence_status"] == "unverified"


def test_analysis_text_has_explicit_upper_bound() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(resume_text="x" * 50_001, job_description="SQL required")
