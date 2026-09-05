"""Data tool registry aggregating ingestion, inspection, cleaning, transformation, analysis, and verification."""

from typing import Optional

from xeren.plugins.data.tools.analysis import DataAnalysisTool
from xeren.plugins.data.tools.cleaning import DataCleaningTool
from xeren.plugins.data.tools.ingestion import DataIngestionTool
from xeren.plugins.data.tools.inspection import DataInspectionTool
from xeren.plugins.data.tools.transformation import DataTransformationTool
from xeren.plugins.data.tools.verification import DataVerificationTool
from xeren.plugins.data.tools.visualization import DataVisualizationTool


class DataToolRegistry:
    """Coordinates modular data processing, analysis, and verification tools."""

    def __init__(
        self,
        ingestion_tool: Optional[DataIngestionTool] = None,
        inspection_tool: Optional[DataInspectionTool] = None,
        cleaning_tool: Optional[DataCleaningTool] = None,
        transformation_tool: Optional[DataTransformationTool] = None,
        analysis_tool: Optional[DataAnalysisTool] = None,
        visualization_tool: Optional[DataVisualizationTool] = None,
        verification_tool: Optional[DataVerificationTool] = None,
    ) -> None:
        self.ingestion_tool = ingestion_tool or DataIngestionTool()
        self.inspection_tool = inspection_tool or DataInspectionTool()
        self.cleaning_tool = cleaning_tool or DataCleaningTool()
        self.transformation_tool = transformation_tool or DataTransformationTool()
        self.analysis_tool = analysis_tool or DataAnalysisTool()
        self.visualization_tool = visualization_tool or DataVisualizationTool()
        self.verification_tool = verification_tool or DataVerificationTool()


__all__ = ["DataToolRegistry"]
