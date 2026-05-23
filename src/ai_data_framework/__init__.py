"""AI Data Framework - Framework analítico orientado a hipóteses."""

__version__ = "0.1.0"

from ai_data_framework.core.entities import (
    Dataset,
    DataQualityMetrics,
    Hypothesis,
    HypothesisStatus,
    Insight,
    PipelineContext,
    ValidationResult,
)
from ai_data_framework.pipeline.orchestrator import AnalyticsPipeline

__all__ = [
    "Dataset",
    "DataQualityMetrics",
    "Hypothesis",
    "HypothesisStatus",
    "Insight",
    "PipelineContext",
    "ValidationResult",
    "AnalyticsPipeline",
]