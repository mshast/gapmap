"""Part 2's single analysis service boundary."""

from gapmap.apps.api.services.analysis.schema import AnalysisResult
from gapmap.apps.api.services.analysis.service import StructuredAnalysisService

__all__ = ["AnalysisResult", "StructuredAnalysisService"]
