"""Private extraction schema and the Part 4 public result contract.

The extraction model deliberately has no scoring, status, action, or project fields.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from gapmap.apps.api.contracts import AnalysisDraft, RequirementType, StrictModel


AnalysisResult = AnalysisDraft
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Quote = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class SkillID(StrEnum):
    SQL_JOINS = "sql_joins"
    SQL_FILTERING = "sql_filtering"
    SQL_AGGREGATION = "sql_aggregation"
    SQL_REFUND_EDGE_CASES = "sql_refund_edge_cases"
    PYTHON = "python"
    REACT = "react"
    DOCKER = "docker"
    DSA = "dsa"
    OTHER = "other"


_ALIASES = {
    "sql": ["sql_joins", "sql_filtering", "sql_aggregation"],
    "postgresql": ["sql_joins", "sql_filtering", "sql_aggregation"],
    "mysql": ["sql_joins", "sql_filtering", "sql_aggregation"],
    "joins": ["sql_joins"],
    "join": ["sql_joins"],
    "filtering": ["sql_filtering"],
    "where": ["sql_filtering"],
    "aggregation": ["sql_aggregation"],
    "group_by": ["sql_aggregation"],
    "refunds": ["sql_refund_edge_cases"],
    "react.js": ["react"],
    "reactjs": ["react"],
    "python3": ["python"],
    "data_structures_and_algorithms": ["dsa"],
}


class ExtractedRequirement(StrictModel):
    label: ShortText
    job_quote: Quote
    importance: Annotated[int, Field(strict=True, ge=1, le=3)]
    requirement_type: RequirementType
    skill_ids: list[SkillID] = Field(min_length=1, max_length=9)
    resume_quotes: list[Quote] = Field(max_length=4)

    @field_validator("skill_ids", mode="before")
    @classmethod
    def canonicalize_skills(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        canonical = []
        for item in value:
            if not isinstance(item, str):
                return value
            key = item.strip().lower().replace(" ", "_").replace("-", "_")
            canonical.extend(_ALIASES.get(key, [key]))
        return list(dict.fromkeys(canonical))


class ExtractionResult(StrictModel):
    target_role: ShortText
    requirements: list[ExtractedRequirement] = Field(min_length=5, max_length=8)
