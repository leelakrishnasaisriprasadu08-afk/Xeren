"""Pydantic schemas for the Xeren Research Plugin."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResearchDepth(str, Enum):
    """Depth levels for research workflow investigation."""

    OVERVIEW = "overview"
    STANDARD = "standard"
    DEEP_DIVE = "deep_dive"


class ResearchInput(BaseModel):
    """Input parameters for activating the Research Plugin."""

    query: str = Field(..., min_length=2, description="The research question, objective, or topic")
    depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Depth of research: overview (fast), standard, or deep_dive (thorough)",
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of candidate sources to select and analyze",
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Optional list of domain filters (e.g. ['arxiv.org', 'wikipedia.org'])",
    )
    min_relevance_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold for selected sources",
    )
    time_limit_seconds: Optional[float] = Field(
        default=30.0,
        gt=0.0,
        description="Execution timeout limit in seconds",
    )
    include_raw_sources: bool = Field(
        default=True,
        description="Whether to include full ranked source objects in the result",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional contextual metadata passed by Xeren Core",
    )


class SearchQuery(BaseModel):
    """An individual search query generated during the research workflow."""

    query_text: str = Field(..., description="Search query string")
    intent: str = Field(default="general", description="Purpose or intent of query (e.g. overview, evidence, contrast)")
    priority: int = Field(default=1, ge=1, description="Execution priority order")


class RawSearchResult(BaseModel):
    """Raw source item retrieved from an external search adapter."""

    url: str = Field(..., description="Web URL or document locator")
    title: str = Field(..., description="Document or web page title")
    snippet: str = Field(..., description="Brief snippet or excerpt")
    full_content: Optional[str] = Field(default=None, description="Full page or document text if retrieved")
    published_date: Optional[str] = Field(default=None, description="Publication or update date")
    author: Optional[str] = Field(default=None, description="Author or source organization")
    score: float = Field(default=0.0, description="Initial provider relevance score")


class RankedSource(BaseModel):
    """A scored and filtered source result with provenance metadata."""

    source_id: str = Field(..., description="Unique source identifier (e.g. 'src-1') for citation reference")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Source title")
    snippet: str = Field(..., description="Relevant text excerpt")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Computed relevance score")
    selected: bool = Field(default=True, description="Whether this source was selected for evidence extraction")
    relevance_rationale: Optional[str] = Field(default=None, description="Explanation for score assignment")


class EvidenceItem(BaseModel):
    """Discrete factual evidence extracted from a source document."""

    evidence_id: str = Field(..., description="Unique identifier (e.g. 'ev-1')")
    fact_statement: str = Field(..., description="Extracted atomic fact, statistic, or verified statement")
    source_id: str = Field(..., description="Associated RankedSource source_id")
    source_url: str = Field(..., description="Direct URL of the source")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for this factual claim")
    citation_marker: str = Field(..., description="Citation bracket marker (e.g. '[1]')")
    context_passage: Optional[str] = Field(default=None, description="Surrounding passage from source text")


class KeyFinding(BaseModel):
    """Thematic finding synthesized from multiple evidence pieces."""

    topic: str = Field(..., description="Theme, topic, or sub-question header")
    summary: str = Field(..., description="Synthesized finding narrative")
    supporting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of evidence_ids directly supporting this finding",
    )
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score in [0.0, 1.0]")


class ResearchResult(BaseModel):
    """Comprehensive structured output produced by the Research Plugin."""

    objective: str = Field(..., description="Interpreted research objective")
    executive_summary: str = Field(..., description="High-level executive summary of all findings")
    findings: List[KeyFinding] = Field(default_factory=list, description="Structured thematic findings")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Atomic factual evidence items")
    sources: List[RankedSource] = Field(default_factory=list, description="Ranked and analyzed sources")
    queries_executed: List[str] = Field(default_factory=list, description="Search queries executed during workflow")
    knowledge_gaps: List[str] = Field(
        default_factory=list,
        description="Identified uncertainties or topics requiring further research",
    )
    contradictions: List[str] = Field(
        default_factory=list,
        description="Noted contradictions or discrepancies across sources",
    )
    confidence_score: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Overall synthesis confidence score",
    )
    execution_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance metrics (latency_ms, sources_analyzed, evidence_count)",
    )

    def to_markdown_report(self) -> str:
        """Format research results as an executive markdown report."""
        lines = [
            f"# Research Report: {self.objective}",
            "",
            "## Executive Summary",
            self.executive_summary,
            "",
            "## Key Findings",
        ]
        for finding in self.findings:
            lines.append(f"### {finding.topic} (Confidence: {finding.confidence:.0%})")
            lines.append(finding.summary)
            if finding.supporting_evidence_ids:
                lines.append(f"*Supporting Evidence: {', '.join(finding.supporting_evidence_ids)}*")
            lines.append("")

        if self.evidence:
            lines.append("## Evidence & Citations")
            for ev in self.evidence:
                lines.append(f"- **{ev.citation_marker}** {ev.fact_statement} ({ev.source_url})")
            lines.append("")

        if self.knowledge_gaps:
            lines.append("## Knowledge Gaps & Limitations")
            for gap in self.knowledge_gaps:
                lines.append(f"- {gap}")
            lines.append("")

        if self.contradictions:
            lines.append("## Discrepancies & Contradictions")
            for item in self.contradictions:
                lines.append(f"- {item}")
            lines.append("")

        lines.append("## References")
        for src in self.sources:
            if src.selected:
                lines.append(f"- [{src.source_id}] [{src.title}]({src.url}) (Relevance: {src.relevance_score:.2f})")

        return "\n".join(lines)


__all__ = [
    "ResearchDepth",
    "ResearchInput",
    "SearchQuery",
    "RawSearchResult",
    "RankedSource",
    "EvidenceItem",
    "KeyFinding",
    "ResearchResult",
]
