"""Data schemas and report structures for the Xeren evaluation framework."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from xeren.models.types import TokenUsage
from xeren.rag.context.types import Citation
from xeren.rag.retrieval.types import SearchResult


class EvalSample(BaseModel):
    """A single evaluation dataset test case."""

    sample_id: str = Field(..., description="Unique identifier for the evaluation item")
    query: str = Field(..., description="User query or test question")
    ground_truth_answer: Optional[str] = Field(default=None, description="Expected reference answer")
    expected_source_ids: List[str] = Field(
        default_factory=list, description="Expected source IDs or document identifiers"
    )
    retrieved_chunks: List[SearchResult] = Field(
        default_factory=list, description="Chunks returned by the retriever"
    )
    generated_answer: Optional[str] = Field(
        default=None, description="Model-generated output answer"
    )
    citations: List[Citation] = Field(
        default_factory=list, description="Citations accompanying the generated answer"
    )
    latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Latency in milliseconds")
    token_usage: Optional[TokenUsage] = Field(default=None, description="Token consumption metrics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary evaluation metadata")


class MetricResult(BaseModel):
    """Result of an individual metric evaluation."""

    metric_name: str = Field(..., description="Name of the metric (e.g. hit_rate@3, token_f1)")
    score: float = Field(..., description="Calculated metric score (usually in [0, 1])")
    passed: Optional[bool] = Field(default=None, description="Whether metric met target threshold")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic scoring details")


class SampleEvaluation(BaseModel):
    """Aggregated evaluation results for a single test sample."""

    sample_id: str = Field(..., description="Sample ID evaluated")
    metrics: Dict[str, MetricResult] = Field(default_factory=dict, description="Map of metric results")


class EvaluationReport(BaseModel):
    """Dataset-level evaluation summary report."""

    benchmark_name: str = Field(..., description="Name of the benchmark or evaluation run")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of evaluation execution",
    )
    total_samples: int = Field(default=0, ge=0, description="Total number of evaluated samples")
    aggregate_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Averaged or percentile metric scores across all samples"
    )
    sample_evaluations: List[SampleEvaluation] = Field(
        default_factory=list, description="Per-sample evaluation results"
    )
    summary_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Run configuration, model IDs, parameters"
    )

    def to_markdown(self) -> str:
        """Render evaluation report as a clean GitHub-flavored markdown table."""
        lines = [
            f"# Evaluation Report: {self.benchmark_name}",
            f"**Executed At:** {self.timestamp.isoformat()}",
            f"**Total Samples:** {self.total_samples}",
            "",
            "## Summary Metrics",
            "| Metric | Score |",
            "| :--- | :--- |",
        ]
        for metric, score in sorted(self.aggregate_metrics.items()):
            lines.append(f"| `{metric}` | {score:.4f} |")

        if self.summary_metadata:
            lines.extend([
                "",
                "## Configuration Details",
                "```json",
                json.dumps(self.summary_metadata, indent=2),
                "```",
            ])

        return "\n".join(lines)
