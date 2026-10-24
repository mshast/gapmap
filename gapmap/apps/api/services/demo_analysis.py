"""Compatibility adapter for explicitly enabled, labeled offline demo analysis."""

from gapmap.apps.api.services.analysis import StructuredAnalysisService


class DemoAnalysisService(StructuredAnalysisService):
    def __init__(self) -> None:
        super().__init__(demo_mode=True)
