"""Xeren Core orchestrator managing plugins, models, and workflows."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel

from xeren.core.context import CoreContext
from xeren.models.base import BaseLLM
from xeren.models.providers.mock import MockLLM
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import (
    CodingInput,
    CodingOperation,
    CodingResult,
    ExecutionConfig,
    FileArtifact,
)
from xeren.plugins.data.plugin import DataPlugin
from xeren.plugins.data.schemas import (
    ChartSpec,
    ChartType,
    CleaningRule,
    DataFormat,
    DataInput,
    DataOperation,
    DataResult,
    DataValidationRule,
    StructuredDataset,
    TransformConfig,
)
from xeren.plugins.errors import PluginExecutionError
from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.schemas import (
    KnowledgeInput,
    KnowledgeOperation,
    KnowledgeResult,
    RetrievalMode,
)
from xeren.plugins.manager import PluginManager
from xeren.plugins.research.plugin import ResearchPlugin
from xeren.plugins.research.schemas import ResearchDepth, ResearchInput, ResearchResult
from xeren.plugins.research.tools.search import BaseSearchEngine
from xeren.plugins.website.plugin import WebsitePlugin
from xeren.plugins.website.schemas import (
    WebsiteInput,
    WebsiteOperation,
    WebsiteResult,
    WebsiteType,
)
from xeren.rag.document import Document
from xeren.rag.retrieval.filter import MetadataFilter

logger = logging.getLogger("xeren.core")


class XerenCore:
    """Central Xeren Core orchestrator.

    Integrates model providers with the modular plugin system, exposing a clean
    unified execution interface.
    """

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        plugin_manager: Optional[PluginManager] = None,
        plugins: Optional[Sequence[BasePlugin]] = None,
        auto_register_defaults: bool = True,
        search_engine: Optional[BaseSearchEngine] = None,
    ) -> None:
        self.llm = llm or MockLLM()
        self.plugin_manager = plugin_manager or PluginManager()
        self.context = CoreContext(llm=self.llm)

        # Register any custom plugins passed in
        if plugins:
            for p in plugins:
                self.register_plugin(p)

        # Auto-register default foundational plugins if not already present
        if auto_register_defaults:
            if not self.plugin_manager.has("research"):
                research_plugin = ResearchPlugin(llm=self.llm, search_engine=search_engine)
                self.register_plugin(research_plugin)
            if not self.plugin_manager.has("knowledge"):
                knowledge_plugin = KnowledgePlugin()
                self.register_plugin(knowledge_plugin)
            if not self.plugin_manager.has("coding"):
                coding_plugin = CodingPlugin(llm=self.llm)
                self.register_plugin(coding_plugin)
            if not self.plugin_manager.has("website"):
                coding_p = self.plugin_manager.get("coding")
                website_plugin = WebsitePlugin(
                    llm=self.llm,
                    coding_plugin=coding_p if isinstance(coding_p, CodingPlugin) else None,
                )
                self.register_plugin(website_plugin)
            if not self.plugin_manager.has("data"):
                data_plugin = DataPlugin()
                self.register_plugin(data_plugin)

    def set_llm(self, llm: BaseLLM) -> None:
        """Replace the active Core LLM (e.g. when injecting the trained Xeren model)."""
        self.llm = llm
        self.context.llm = llm
        # Update LLM across registered plugins that support it
        research = self.plugin_manager.get("research")
        if isinstance(research, ResearchPlugin):
            research.set_llm(llm)
        coding = self.plugin_manager.get("coding")
        if isinstance(coding, CodingPlugin):
            coding.set_llm(llm)
        website = self.plugin_manager.get("website")
        if isinstance(website, WebsitePlugin):
            website.set_llm(llm)

    def set_search_engine(self, engine: BaseSearchEngine) -> None:
        """Replace the active search engine across registered research plugins."""
        research = self.plugin_manager.get("research")
        if isinstance(research, ResearchPlugin):
            research.set_search_engine(engine)

    # -------------------------------------------------------------------------
    # Extensible Plugin Management (Open for any future plugins)
    # -------------------------------------------------------------------------
    def register_plugin(self, plugin: BasePlugin, override: bool = False) -> None:
        """Register a new plugin with the Core."""
        self.plugin_manager.register(plugin, override=override)

    def unregister_plugin(self, name: str) -> Optional[BasePlugin]:
        """Unregister a plugin by name."""
        return self.plugin_manager.unregister(name)

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Retrieve a registered plugin by name."""
        return self.plugin_manager.get(name)

    def list_plugins(self) -> List[PluginManifest]:
        """List manifests of all registered plugins."""
        return self.plugin_manager.list_plugins()

    def has_plugin(self, name: str) -> bool:
        """Check whether a plugin is registered."""
        return self.plugin_manager.has(name)

    # -------------------------------------------------------------------------
    # Generic Plugin Execution
    # -------------------------------------------------------------------------
    def execute_plugin(
        self,
        name: str,
        input_data: Union[BaseModel, Dict[str, Any]],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PluginExecutionResult:
        """Execute any registered plugin through the PluginManager."""
        ctx = PluginExecutionContext(
            llm=self.llm,
            timeout_seconds=timeout,
            metadata=metadata or {},
        )
        return self.plugin_manager.execute(name, input_data, context=ctx, timeout=timeout)

    async def aexecute_plugin(
        self,
        name: str,
        input_data: Union[BaseModel, Dict[str, Any]],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute any registered plugin through the PluginManager."""
        ctx = PluginExecutionContext(
            llm=self.llm,
            timeout_seconds=timeout,
            metadata=metadata or {},
        )
        return await self.plugin_manager.aexecute(name, input_data, context=ctx, timeout=timeout)

    # -------------------------------------------------------------------------
    # High-level Research Capability
    # -------------------------------------------------------------------------
    def research(
        self,
        query: str,
        depth: Union[ResearchDepth, str] = ResearchDepth.STANDARD,
        max_sources: int = 5,
        domains: Optional[List[str]] = None,
        min_relevance_score: float = 0.3,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> ResearchResult:
        """Execute autonomous research using the registered ResearchPlugin."""
        depth_enum = ResearchDepth(depth) if isinstance(depth, str) else depth
        research_input = ResearchInput(
            query=query,
            depth=depth_enum,
            max_sources=max_sources,
            domains=domains or [],
            min_relevance_score=min_relevance_score,
            time_limit_seconds=timeout,
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("research", research_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, ResearchResult):
            raise PluginExecutionError(
                f"Research execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="research",
            )
        return exec_res.output

    async def aresearch(
        self,
        query: str,
        depth: Union[ResearchDepth, str] = ResearchDepth.STANDARD,
        max_sources: int = 5,
        domains: Optional[List[str]] = None,
        min_relevance_score: float = 0.3,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> ResearchResult:
        """Asynchronously execute autonomous research using the registered ResearchPlugin."""
        depth_enum = ResearchDepth(depth) if isinstance(depth, str) else depth
        research_input = ResearchInput(
            query=query,
            depth=depth_enum,
            max_sources=max_sources,
            domains=domains or [],
            min_relevance_score=min_relevance_score,
            time_limit_seconds=timeout,
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("research", research_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, ResearchResult):
            raise PluginExecutionError(
                f"Async research execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="research",
            )
        return exec_res.output

    # -------------------------------------------------------------------------
    # High-level Knowledge / RAG Capability
    # -------------------------------------------------------------------------
    def knowledge(
        self,
        query: str,
        top_k: int = 5,
        top_n: Optional[int] = 5,
        retrieval_mode: Union[RetrievalMode, str] = RetrievalMode.HYBRID,
        min_score: float = 0.0,
        filter: Optional[MetadataFilter] = None,
        include_context: bool = True,
        include_provenance: bool = True,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> KnowledgeResult:
        """Execute knowledge retrieval using the registered KnowledgePlugin."""
        mode = RetrievalMode(retrieval_mode) if isinstance(retrieval_mode, str) else retrieval_mode
        knowledge_input = KnowledgeInput(
            query=query,
            operation=KnowledgeOperation.QUERY,
            top_k=top_k,
            top_n=top_n,
            retrieval_mode=mode,
            min_score=min_score,
            filter=filter,
            include_context=include_context,
            include_provenance=include_provenance,
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("knowledge", knowledge_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, KnowledgeResult):
            raise PluginExecutionError(
                f"Knowledge execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="knowledge",
            )
        return exec_res.output

    async def aknowledge(
        self,
        query: str,
        top_k: int = 5,
        top_n: Optional[int] = 5,
        retrieval_mode: Union[RetrievalMode, str] = RetrievalMode.HYBRID,
        min_score: float = 0.0,
        filter: Optional[MetadataFilter] = None,
        include_context: bool = True,
        include_provenance: bool = True,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> KnowledgeResult:
        """Asynchronously execute knowledge retrieval using the registered KnowledgePlugin."""
        mode = RetrievalMode(retrieval_mode) if isinstance(retrieval_mode, str) else retrieval_mode
        knowledge_input = KnowledgeInput(
            query=query,
            operation=KnowledgeOperation.QUERY,
            top_k=top_k,
            top_n=top_n,
            retrieval_mode=mode,
            min_score=min_score,
            filter=filter,
            include_context=include_context,
            include_provenance=include_provenance,
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("knowledge", knowledge_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, KnowledgeResult):
            raise PluginExecutionError(
                f"Async knowledge execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="knowledge",
            )
        return exec_res.output

    def ingest_knowledge(
        self,
        texts: Optional[List[str]] = None,
        documents: Optional[List[Document]] = None,
        source: str = "knowledge_ingest",
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> KnowledgeResult:
        """Ingest documents or raw texts into the knowledge base via KnowledgePlugin."""
        knowledge_input = KnowledgeInput(
            operation=KnowledgeOperation.INGEST,
            texts=texts,
            documents=documents,
            source=source,
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("knowledge", knowledge_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, KnowledgeResult):
            raise PluginExecutionError(
                f"Knowledge ingestion failed: {exec_res.error or 'Unknown error'}",
                plugin_name="knowledge",
            )
        return exec_res.output

    async def aingest_knowledge(
        self,
        texts: Optional[List[str]] = None,
        documents: Optional[List[Document]] = None,
        source: str = "knowledge_ingest",
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> KnowledgeResult:
        """Asynchronously ingest documents or raw texts into the knowledge base."""
        knowledge_input = KnowledgeInput(
            operation=KnowledgeOperation.INGEST,
            texts=texts,
            documents=documents,
            source=source,
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("knowledge", knowledge_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, KnowledgeResult):
            raise PluginExecutionError(
                f"Async knowledge ingestion failed: {exec_res.error or 'Unknown error'}",
                plugin_name="knowledge",
            )
        return exec_res.output

    # -------------------------------------------------------------------------
    # High-level Coding Capability
    # -------------------------------------------------------------------------
    def coding(
        self,
        task: str = "",
        operation: Union[CodingOperation, str] = CodingOperation.GENERATE,
        language: str = "python",
        source_code: Optional[str] = None,
        source_files: Optional[List[FileArtifact]] = None,
        entrypoint: Optional[str] = None,
        test_code: Optional[str] = None,
        test_command: Optional[str] = None,
        execution_config: Optional[ExecutionConfig] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> CodingResult:
        """Execute autonomous coding operations using the registered CodingPlugin."""
        op_enum = CodingOperation(operation) if isinstance(operation, str) else operation
        coding_input = CodingInput(
            task=task,
            operation=op_enum,
            language=language,
            source_code=source_code,
            source_files=source_files or [],
            entrypoint=entrypoint,
            test_code=test_code,
            test_command=test_command,
            execution_config=execution_config or ExecutionConfig(),
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("coding", coding_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, CodingResult):
            raise PluginExecutionError(
                f"Coding execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="coding",
            )
        return exec_res.output

    async def acoding(
        self,
        task: str = "",
        operation: Union[CodingOperation, str] = CodingOperation.GENERATE,
        language: str = "python",
        source_code: Optional[str] = None,
        source_files: Optional[List[FileArtifact]] = None,
        entrypoint: Optional[str] = None,
        test_code: Optional[str] = None,
        test_command: Optional[str] = None,
        execution_config: Optional[ExecutionConfig] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> CodingResult:
        """Asynchronously execute autonomous coding operations."""
        op_enum = CodingOperation(operation) if isinstance(operation, str) else operation
        coding_input = CodingInput(
            task=task,
            operation=op_enum,
            language=language,
            source_code=source_code,
            source_files=source_files or [],
            entrypoint=entrypoint,
            test_code=test_code,
            test_command=test_command,
            execution_config=execution_config or ExecutionConfig(),
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("coding", coding_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, CodingResult):
            raise PluginExecutionError(
                f"Async coding execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="coding",
            )
        return exec_res.output

    # -------------------------------------------------------------------------
    # High-level Website Capability
    # -------------------------------------------------------------------------
    def website(
        self,
        requirement: str = "",
        operation: Union[WebsiteOperation, str] = WebsiteOperation.GENERATE,
        website_type: Union[WebsiteType, str] = WebsiteType.LANDING_PAGE,
        pages: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        existing_files: Optional[List[FileArtifact]] = None,
        modification_request: Optional[str] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> WebsiteResult:
        """Execute website operations using the registered WebsitePlugin."""
        op_enum = WebsiteOperation(operation) if isinstance(operation, str) else operation
        type_enum = WebsiteType(website_type) if isinstance(website_type, str) else website_type
        web_input = WebsiteInput(
            requirement=requirement,
            operation=op_enum,
            website_type=type_enum,
            pages=pages or [],
            features=features or [],
            existing_files=existing_files or [],
            modification_request=modification_request,
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("website", web_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, WebsiteResult):
            raise PluginExecutionError(
                f"Website execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="website",
            )
        return exec_res.output

    async def awebsite(
        self,
        requirement: str = "",
        operation: Union[WebsiteOperation, str] = WebsiteOperation.GENERATE,
        website_type: Union[WebsiteType, str] = WebsiteType.LANDING_PAGE,
        pages: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        existing_files: Optional[List[FileArtifact]] = None,
        modification_request: Optional[str] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> WebsiteResult:
        """Asynchronously execute website operations."""
        op_enum = WebsiteOperation(operation) if isinstance(operation, str) else operation
        type_enum = WebsiteType(website_type) if isinstance(website_type, str) else website_type
        web_input = WebsiteInput(
            requirement=requirement,
            operation=op_enum,
            website_type=type_enum,
            pages=pages or [],
            features=features or [],
            existing_files=existing_files or [],
            modification_request=modification_request,
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("website", web_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, WebsiteResult):
            raise PluginExecutionError(
                f"Async website execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="website",
            )
        return exec_res.output

    # -------------------------------------------------------------------------
    # High-level Data Capability
    # -------------------------------------------------------------------------
    def data(
        self,
        operation: Union[DataOperation, str] = DataOperation.INSPECT,
        data: Optional[Union[str, List[Dict[str, Any]], Dict[str, Any]]] = None,
        file_path: Optional[str] = None,
        dataset: Optional[StructuredDataset] = None,
        format: Optional[Union[DataFormat, str]] = None,
        cleaning_rules: Optional[CleaningRule] = None,
        transform_config: Optional[TransformConfig] = None,
        analysis_columns: Optional[List[str]] = None,
        include_correlations: bool = False,
        visualization_spec: Optional[ChartSpec] = None,
        chart_type: Optional[Union[ChartType, str]] = None,
        chart_x: Optional[str] = None,
        chart_y: Optional[str] = None,
        verification_rules: Optional[List[DataValidationRule]] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> DataResult:
        """Execute structured data operations using the registered DataPlugin."""
        op_enum = DataOperation(operation) if isinstance(operation, str) else operation
        fmt_val = DataFormat(format) if isinstance(format, str) else format
        c_type = ChartType(chart_type) if isinstance(chart_type, str) else chart_type

        records = kwargs.pop("records", None)
        data_val = data if data is not None else records

        data_input = DataInput(
            operation=op_enum,
            data=data_val,
            records=records,
            file_path=file_path,
            dataset=dataset,
            format=fmt_val,
            cleaning_rules=cleaning_rules,
            transform_config=transform_config,
            analysis_columns=analysis_columns,
            include_correlations=include_correlations,
            visualization_spec=visualization_spec,
            chart_type=c_type,
            chart_x=chart_x,
            chart_y=chart_y,
            verification_rules=verification_rules,
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("data", data_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, DataResult):
            raise PluginExecutionError(
                f"Data execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="data",
            )
        return exec_res.output

    async def adata(
        self,
        operation: Union[DataOperation, str] = DataOperation.INSPECT,
        data: Optional[Union[str, List[Dict[str, Any]], Dict[str, Any]]] = None,
        file_path: Optional[str] = None,
        dataset: Optional[StructuredDataset] = None,
        format: Optional[Union[DataFormat, str]] = None,
        cleaning_rules: Optional[CleaningRule] = None,
        transform_config: Optional[TransformConfig] = None,
        analysis_columns: Optional[List[str]] = None,
        include_correlations: bool = False,
        visualization_spec: Optional[ChartSpec] = None,
        chart_type: Optional[Union[ChartType, str]] = None,
        chart_x: Optional[str] = None,
        chart_y: Optional[str] = None,
        verification_rules: Optional[List[DataValidationRule]] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> DataResult:
        """Asynchronously execute structured data operations."""
        op_enum = DataOperation(operation) if isinstance(operation, str) else operation
        fmt_val = DataFormat(format) if isinstance(format, str) else format
        c_type = ChartType(chart_type) if isinstance(chart_type, str) else chart_type

        records = kwargs.pop("records", None)
        data_val = data if data is not None else records

        data_input = DataInput(
            operation=op_enum,
            data=data_val,
            records=records,
            file_path=file_path,
            dataset=dataset,
            format=fmt_val,
            cleaning_rules=cleaning_rules,
            transform_config=transform_config,
            analysis_columns=analysis_columns,
            include_correlations=include_correlations,
            visualization_spec=visualization_spec,
            chart_type=c_type,
            chart_x=chart_x,
            chart_y=chart_y,
            verification_rules=verification_rules,
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("data", data_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, DataResult):
            raise PluginExecutionError(
                f"Async data execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="data",
            )
        return exec_res.output

    # -------------------------------------------------------------------------
    # Core Health Check
    # -------------------------------------------------------------------------
    def plugin_health(self) -> Dict[str, HealthCheckResult]:
        """Return health status of all registered plugins."""
        return self.plugin_manager.health_check()

    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health checks across Core LLM and all registered plugins."""
        llm_healthy = self.llm.ping()
        plugin_health = self.plugin_manager.health_check()
        return {
            "core_llm": {"provider": type(self.llm).__name__, "healthy": llm_healthy},
            "plugins": {name: res.model_dump() for name, res in plugin_health.items()},
            "healthy": llm_healthy and all(r.status.value == "healthy" for r in plugin_health.values()),
        }

    async def acheck_health(self) -> Dict[str, Any]:
        """Asynchronously perform health checks."""
        llm_healthy = await self.llm.aping()
        plugin_health = await self.plugin_manager.ahealth_check()
        return {
            "core_llm": {"provider": type(self.llm).__name__, "healthy": llm_healthy},
            "plugins": {name: res.model_dump() for name, res in plugin_health.items()},
            "healthy": llm_healthy and all(r.status.value == "healthy" for r in plugin_health.values()),
        }


__all__ = ["XerenCore"]
