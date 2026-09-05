"""Eight-step autonomous research workflow orchestrator."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from xeren.models.base import BaseLLM
from xeren.plugins.research.schemas import (
    EvidenceItem,
    KeyFinding,
    RankedSource,
    RawSearchResult,
    ResearchDepth,
    ResearchInput,
    ResearchResult,
    SearchQuery,
)
from xeren.plugins.research.tools.registry import ResearchToolRegistry
from xeren.plugins.research.tools.search import BaseSearchEngine

logger = logging.getLogger("xeren.plugins.research.workflow")


class ResearchWorkflow:
    """Implements the complete 8-step autonomous research workflow."""

    def __init__(
        self,
        tool_registry: Optional[ResearchToolRegistry] = None,
        llm: Optional[BaseLLM] = None,
        search_engine: Optional[BaseSearchEngine] = None,
    ) -> None:
        self.registry = tool_registry or ResearchToolRegistry(search_engine=search_engine, llm=llm)
        if llm is not None:
            self.registry.set_llm(llm)
        if search_engine is not None:
            self.registry.set_search_engine(search_engine)

    # -------------------------------------------------------------------------
    # STEP 1: Understand research objective
    # -------------------------------------------------------------------------
    def step_understand_objective(self, research_input: ResearchInput) -> str:
        """Step 1: Parse and articulate the target research objective and constraints."""
        clean_query = research_input.query.strip()
        logger.debug("Step 1: Understood research objective: '%s' (depth: %s)", clean_query, research_input.depth)
        return clean_query

    # -------------------------------------------------------------------------
    # STEP 2: Generate search queries
    # -------------------------------------------------------------------------
    def step_generate_queries(self, objective: str, depth: ResearchDepth) -> List[SearchQuery]:
        """Step 2: Formulate targeted, diverse search queries for multi-angle investigation."""
        queries: List[SearchQuery] = [
            SearchQuery(query_text=objective, intent="primary_overview", priority=1)
        ]

        if depth in (ResearchDepth.STANDARD, ResearchDepth.DEEP_DIVE):
            queries.extend([
                SearchQuery(
                    query_text=f"{objective} empirical data benchmarks",
                    intent="evidence_and_metrics",
                    priority=2,
                ),
                SearchQuery(
                    query_text=f"{objective} analysis and evaluation",
                    intent="analytical_evaluation",
                    priority=3,
                ),
            ])

        if depth == ResearchDepth.DEEP_DIVE:
            queries.extend([
                SearchQuery(
                    query_text=f"{objective} limitations drawbacks challenges",
                    intent="contrasting_views_and_limitations",
                    priority=4,
                ),
                SearchQuery(
                    query_text=f"{objective} state of the art comparison",
                    intent="comparative_context",
                    priority=5,
                ),
            ])

        logger.debug("Step 2: Generated %d search queries for objective '%s'", len(queries), objective)
        return queries

    # -------------------------------------------------------------------------
    # STEP 3 & 4: Execute search capability & collect source results
    # -------------------------------------------------------------------------
    def step_execute_and_collect_search(
        self,
        queries: List[SearchQuery],
        domains: Optional[List[str]] = None,
        max_results_per_query: int = 4,
    ) -> List[RawSearchResult]:
        """Step 3 & 4: Execute queries against abstract search engine and collect raw results."""
        collected_results: List[RawSearchResult] = []
        for query_obj in queries:
            try:
                results = self.registry.search_engine.search(
                    query=query_obj.query_text,
                    max_results=max_results_per_query,
                    domains=domains,
                )
                collected_results.extend(results)
                logger.debug("Executed query '%s', got %d results", query_obj.query_text, len(results))
            except Exception as err:
                logger.warning("Query '%s' search failed: %s", query_obj.query_text, err)

        logger.info("Step 3-4: Collected %d total raw search results", len(collected_results))
        return collected_results

    async def astep_execute_and_collect_search(
        self,
        queries: List[SearchQuery],
        domains: Optional[List[str]] = None,
        max_results_per_query: int = 4,
    ) -> List[RawSearchResult]:
        """Asynchronously execute queries against abstract search engine and collect raw results."""
        collected_results: List[RawSearchResult] = []

        async def _run_search(q: SearchQuery) -> List[RawSearchResult]:
            try:
                return await self.registry.search_engine.asearch(
                    query=q.query_text,
                    max_results=max_results_per_query,
                    domains=domains,
                )
            except Exception as err:
                logger.warning("Async query '%s' search failed: %s", q.query_text, err)
                return []

        search_tasks = [_run_search(q) for q in queries]
        batch_results = await asyncio.gather(*search_tasks)
        for res_list in batch_results:
            collected_results.extend(res_list)

        logger.info("Step 3-4: Async collected %d total raw search results", len(collected_results))
        return collected_results

    # -------------------------------------------------------------------------
    # STEP 5: Rank and retrieve relevant sources
    # -------------------------------------------------------------------------
    def step_rank_sources(
        self,
        objective: str,
        raw_results: List[RawSearchResult],
        max_sources: int = 5,
        min_relevance_score: float = 0.3,
    ) -> List[RankedSource]:
        """Step 5: Rank, deduplicate, and threshold-filter candidate sources using RAG principles."""
        ranked = self.registry.ranking_tool.execute(
            objective=objective,
            results=raw_results,
            max_sources=max_sources,
            min_relevance_score=min_relevance_score,
        )
        logger.info("Step 5: Ranked %d sources (%d selected)", len(ranked), sum(1 for s in ranked if s.selected))
        return ranked

    # -------------------------------------------------------------------------
    # STEP 6: Extract useful evidence
    # -------------------------------------------------------------------------
    def step_extract_evidence(
        self,
        objective: str,
        ranked_sources: List[RankedSource],
        max_evidence_per_source: int = 3,
    ) -> List[EvidenceItem]:
        """Step 6: Extract atomic facts, quotes, and citations from ranked sources."""
        evidence = self.registry.evidence_tool.execute(
            objective=objective,
            sources=ranked_sources,
            max_evidence_per_source=max_evidence_per_source,
        )
        logger.info("Step 6: Extracted %d atomic evidence items", len(evidence))
        return evidence

    # -------------------------------------------------------------------------
    # STEP 7: Produce structured findings
    # -------------------------------------------------------------------------
    def step_synthesize_findings(
        self,
        objective: str,
        evidence: List[EvidenceItem],
        sources: List[RankedSource],
        queries_executed: List[str],
    ) -> Dict[str, Any]:
        """Step 7: Synthesize evidence into structured key findings and executive summary."""
        synthesis_result = self.registry.synthesis_tool.execute(
            objective=objective,
            evidence=evidence,
            sources=sources,
            queries_executed=queries_executed,
        )
        logger.info("Step 7: Synthesized findings with confidence %.2f", synthesis_result.get("confidence_score", 0.0))
        return synthesis_result

    # -------------------------------------------------------------------------
    # STEP 8: Produce and return final structured result to Xeren Core
    # -------------------------------------------------------------------------
    def step_assemble_result(
        self,
        objective: str,
        synthesis: Dict[str, Any],
        evidence: List[EvidenceItem],
        sources: List[RankedSource],
        queries_executed: List[str],
        start_time: float,
        include_raw_sources: bool = True,
    ) -> ResearchResult:
        """Step 8: Construct and validate final ResearchResult object for Xeren Core."""
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        filtered_sources = sources if include_raw_sources else [s for s in sources if s.selected]

        return ResearchResult(
            objective=objective,
            executive_summary=synthesis.get("executive_summary", ""),
            findings=synthesis.get("findings", []),
            evidence=evidence,
            sources=filtered_sources,
            queries_executed=queries_executed,
            knowledge_gaps=synthesis.get("knowledge_gaps", []),
            contradictions=synthesis.get("contradictions", []),
            confidence_score=synthesis.get("confidence_score", 0.85),
            execution_stats={
                "latency_ms": latency_ms,
                "sources_analyzed": len(sources),
                "selected_sources": sum(1 for s in sources if s.selected),
                "evidence_count": len(evidence),
                "queries_count": len(queries_executed),
            },
        )

    # -------------------------------------------------------------------------
    # Full Synchronous Execution
    # -------------------------------------------------------------------------
    def run(self, research_input: ResearchInput) -> ResearchResult:
        """Execute the full 8-step research workflow synchronously."""
        start_time = time.perf_counter()
        logger.info("Starting Research Workflow for query: '%s'", research_input.query)

        # 1. Understand objective
        objective = self.step_understand_objective(research_input)

        # 2. Generate search queries
        queries = self.step_generate_queries(objective, research_input.depth)
        query_texts = [q.query_text for q in queries]

        # 3 & 4. Execute search and collect results
        raw_results = self.step_execute_and_collect_search(
            queries=queries,
            domains=research_input.domains or None,
            max_results_per_query=max(2, research_input.max_sources // len(queries) + 1),
        )

        # 5. Rank and retrieve relevant sources
        ranked_sources = self.step_rank_sources(
            objective=objective,
            raw_results=raw_results,
            max_sources=research_input.max_sources,
            min_relevance_score=research_input.min_relevance_score,
        )

        # 6. Extract useful evidence
        evidence = self.step_extract_evidence(
            objective=objective,
            ranked_sources=ranked_sources,
        )

        # 7. Synthesize findings
        synthesis = self.step_synthesize_findings(
            objective=objective,
            evidence=evidence,
            sources=ranked_sources,
            queries_executed=query_texts,
        )

        # 8. Return structured result
        result = self.step_assemble_result(
            objective=objective,
            synthesis=synthesis,
            evidence=evidence,
            sources=ranked_sources,
            queries_executed=query_texts,
            start_time=start_time,
            include_raw_sources=research_input.include_raw_sources,
        )

        logger.info("Completed Research Workflow in %.2fms", result.execution_stats["latency_ms"])
        return result

    # -------------------------------------------------------------------------
    # Full Asynchronous Execution
    # -------------------------------------------------------------------------
    async def arun(self, research_input: ResearchInput) -> ResearchResult:
        """Execute the full 8-step research workflow asynchronously."""
        start_time = time.perf_counter()
        logger.info("Starting Async Research Workflow for query: '%s'", research_input.query)

        # 1. Understand objective
        objective = self.step_understand_objective(research_input)

        # 2. Generate search queries
        queries = self.step_generate_queries(objective, research_input.depth)
        query_texts = [q.query_text for q in queries]

        # 3 & 4. Async search execution and collection
        raw_results = await self.astep_execute_and_collect_search(
            queries=queries,
            domains=research_input.domains or None,
            max_results_per_query=max(2, research_input.max_sources // len(queries) + 1),
        )

        # 5. Rank and retrieve relevant sources
        ranked_sources = await asyncio.to_thread(
            self.step_rank_sources,
            objective,
            raw_results,
            research_input.max_sources,
            research_input.min_relevance_score,
        )

        # 6. Extract useful evidence
        evidence = await asyncio.to_thread(
            self.step_extract_evidence,
            objective,
            ranked_sources,
        )

        # 7. Synthesize findings
        synthesis = await asyncio.to_thread(
            self.step_synthesize_findings,
            objective,
            evidence,
            ranked_sources,
            query_texts,
        )

        # 8. Return structured result
        result = self.step_assemble_result(
            objective=objective,
            synthesis=synthesis,
            evidence=evidence,
            sources=ranked_sources,
            queries_executed=query_texts,
            start_time=start_time,
            include_raw_sources=research_input.include_raw_sources,
        )

        logger.info("Completed Async Research Workflow in %.2fms", result.execution_stats["latency_ms"])
        return result


__all__ = ["ResearchWorkflow"]
