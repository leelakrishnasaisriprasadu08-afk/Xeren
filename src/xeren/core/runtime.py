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
from xeren.plugins.api.plugin import ApiPlugin
from xeren.plugins.api.schemas import (
    ApiError,
    ApiHealthReport,
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyEnvironment,
    ApiKeyMetadata,
    ApiKeyRevokeRequest,
    ApiKeyRotateRequest,
    ApiInput,
    ApiOperation,
    ApiRequest,
    ApiResponse,
    ApiResult,
    ApiScope,
)
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.automation.schemas import (
    AutomationInput,
    AutomationOperation,
    AutomationResult,
    TaskPlan,
    TaskStep,
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
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
    ExperienceStats,
    FailureWarning,
    LessonItem,
    UserFeedback,
)
from xeren.plugins.file.plugin import FilePlugin
from xeren.plugins.file.schemas import (
    FileInput,
    FileItemMetadata,
    FileOperation,
    FileResult,
    SearchResultItem,
)
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
from xeren.plugins.verification.plugin import VerificationPlugin
from xeren.plugins.verification.schemas import (
    CandidateItem,
    EvidenceItem,
    VerificationInput,
    VerificationOperation,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.website.plugin import WebsitePlugin
from xeren.plugins.website.schemas import (
    WebsiteInput,
    WebsiteOperation,
    WebsiteResult,
    WebsiteType,
)
from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.controller import AgentController
from xeren.agent.permissions import PermissionManager
from xeren.agent.plugins.experience import ExperienceInput, ExperiencePlugin
from xeren.agent.plugins.verification import VerificationInput, VerificationPlugin
from xeren.agent.types import AgentState, AgentStatus
from xeren.core.planner import CorePlannerAdapter, TaskPlan
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
 evalution&tesing
            if not self.plugin_manager.has("verification"):
                self.register_plugin(VerificationPlugin())
            if not self.plugin_manager.has("experience"):
                self.register_plugin(ExperiencePlugin())

            if not self.plugin_manager.has("file"):
                file_plugin = FilePlugin()
                self.register_plugin(file_plugin)
            if not self.plugin_manager.has("verification"):
                verification_plugin = VerificationPlugin(llm=self.llm)
                self.register_plugin(verification_plugin)
            if not self.plugin_manager.has("experience"):
                experience_plugin = ExperiencePlugin()
                self.register_plugin(experience_plugin)
            if not self.plugin_manager.has("automation"):
                automation_plugin = AutomationPlugin(plugin_manager=self.plugin_manager)
                self.register_plugin(automation_plugin)
            if not self.plugin_manager.has("api"):
                api_plugin = ApiPlugin(plugin_manager=self.plugin_manager)
                api_plugin.set_core(self)
                self.register_plugin(api_plugin)
 main

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
        verification = self.plugin_manager.get("verification")
        if isinstance(verification, VerificationPlugin):
            verification.set_llm(llm)

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
        if isinstance(plugin, AutomationPlugin) and plugin.registry.plugin_manager is None:
            plugin.set_plugin_manager(self.plugin_manager)
        if isinstance(plugin, ApiPlugin):
            if plugin.registry.plugin_manager is None:
                plugin.set_plugin_manager(self.plugin_manager)
            plugin.set_core(self)
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
 evalution&tesing
    # Autonomous Agent Target Flow Orchestration
    # User Goal -> Xeren Core -> CorePlannerAdapter -> TaskPlan ->
    # AgentController -> PluginManager -> Required Plugin(s) ->
    # Verification -> Experience -> Result
    # -------------------------------------------------------------------------
    def _ensure_agent_plugins(self) -> None:
        """Auto-register VerificationPlugin and ExperiencePlugin if not already registered."""
        if not self.plugin_manager.has("verification"):
            self.register_plugin(VerificationPlugin())
        if not self.plugin_manager.has("experience"):
            self.register_plugin(ExperiencePlugin())

    async def arun_agent(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        browser_adapter: Optional[BaseBrowserAdapter] = None,
        permission_manager: Optional[PermissionManager] = None,
        planner_adapter: Optional[CorePlannerAdapter] = None,
        verify_outcome: bool = True,
        record_experience: bool = True,
        max_steps: int = 15,
    ) -> Dict[str, Any]:
        """Asynchronously execute the complete autonomous agent workflow."""
        self._ensure_agent_plugins()
        ctx = dict(context or {})

        # 1. Initialize CorePlannerAdapter
        planner = planner_adapter or CorePlannerAdapter(
            llm=self.llm,
            plugin_manager=self.plugin_manager,
        )

        # 2. Produce and validate TaskPlan
        task_plan = await planner.acreate_task_plan(goal, ctx)

        # 3. Initialize Browser & Controller
        browser = browser_adapter or MockBrowserAdapter()
        controller = AgentController(
            browser_adapter=browser,
            planner=planner,
            plugin_manager=self.plugin_manager,
            permission_manager=permission_manager,
            max_steps=max_steps,
        )

        # 4. Execute through AgentController
        state = await controller.arun(
            task=goal,
            context={"task_plan": task_plan, **ctx},
            max_steps=max_steps,
        )

        # 5. Verification step
        verification_output: Any = None
        if verify_outcome and self.plugin_manager.has("verification"):
            v_input = VerificationInput(
                task=goal,
                success=(state.status == AgentStatus.COMPLETED),
                expected_conditions=ctx.get("expected_conditions", []),
                actual_data=state.memory,
            )
            v_res = await self.plugin_manager.aexecute("verification", v_input)
            if v_res.success and v_res.output:
                verification_output = v_res.output

        # 6. Experience recording step
        experience_output: Any = None
        if record_experience and self.plugin_manager.has("experience"):
            v_passed = (
                verification_output.verified
                if verification_output and hasattr(verification_output, "verified")
                else (state.status == AgentStatus.COMPLETED)
            )
            exp_input = ExperienceInput(
                state=state.model_dump(),
                prediction_confidence=0.95,
                final_quality_score=1.0 if state.status == AgentStatus.COMPLETED else 0.0,
                split=ctx.get("split", "train"),
                verification_passed=v_passed,
            )
            exp_res = await self.plugin_manager.aexecute("experience", exp_input)
            if exp_res.success and exp_res.output:
                experience_output = exp_res.output

        # 7. Final response synthesis
        final_response: str = ""
        if state.status == AgentStatus.COMPLETED:
            if state.memory.get("final_response"):
                final_response = str(state.memory["final_response"])
            elif state.history:
                _, last_res = state.history[-1]
                if last_res.data:
                    final_response = f"Successfully completed: {last_res.data}"
                elif last_res.observation and last_res.observation.text_content:
                    final_response = f"Observation: {last_res.observation.text_content[:200]}"
                else:
                    final_response = f"Successfully executed task: {goal}"
            else:
                final_response = f"Successfully executed task: {goal}"
        else:
            reason = state.metadata.get("completion_reason", "Task execution did not complete successfully.")
            final_response = f"Task failed: {reason}"

        # 8. Final structured result
        return {
            "success": state.status == AgentStatus.COMPLETED,
            "goal": goal,
            "plan": task_plan,
            "state": state,
            "verification": verification_output,
            "experience": experience_output,
            "final_response": final_response,
            "error": state.metadata.get("completion_reason") if state.status != AgentStatus.COMPLETED else None,
        }

    def run_agent(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        browser_adapter: Optional[BaseBrowserAdapter] = None,
        permission_manager: Optional[PermissionManager] = None,
        planner_adapter: Optional[CorePlannerAdapter] = None,
        verify_outcome: bool = True,
        record_experience: bool = True,
        max_steps: int = 15,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for arun_agent."""
        return asyncio.run(
            self.arun_agent(
                goal=goal,
                context=context,
                browser_adapter=browser_adapter,
                permission_manager=permission_manager,
                planner_adapter=planner_adapter,
                verify_outcome=verify_outcome,
                record_experience=record_experience,
                max_steps=max_steps,
            )
        )

    async def aprocess_request(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
        browser_adapter: Optional[BaseBrowserAdapter] = None,
        permission_manager: Optional[PermissionManager] = None,
        planner_adapter: Optional[CorePlannerAdapter] = None,
        verify_outcome: bool = True,
        record_experience: bool = True,
        max_steps: int = 15,
    ) -> Dict[str, Any]:
        """Unified end-to-end processing pipeline:
        User Request -> Xeren Core -> Reasoning/Planning -> Autonomous Agent ->
        Plugin Manager -> Capabilities -> Verification -> Experience -> Final Response.
        """
        return await self.arun_agent(
            goal=request,
            context=context,
            browser_adapter=browser_adapter,
            permission_manager=permission_manager,
            planner_adapter=planner_adapter,
            verify_outcome=verify_outcome,
            record_experience=record_experience,
            max_steps=max_steps,
        )

    def process_request(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
        browser_adapter: Optional[BaseBrowserAdapter] = None,
        permission_manager: Optional[PermissionManager] = None,
        planner_adapter: Optional[CorePlannerAdapter] = None,
        verify_outcome: bool = True,
        record_experience: bool = True,
        max_steps: int = 15,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for aprocess_request."""
        return asyncio.run(
            self.aprocess_request(
                request=request,
                context=context,
                browser_adapter=browser_adapter,
                permission_manager=permission_manager,
                planner_adapter=planner_adapter,
                verify_outcome=verify_outcome,
                record_experience=record_experience,
                max_steps=max_steps,
            )

    # High-level File Capability
    # -------------------------------------------------------------------------
    def file(
        self,
        operation: Union[FileOperation, str] = FileOperation.READ,
        path: Optional[str] = None,
        destination_path: Optional[str] = None,
        content: Optional[str] = None,
        encoding: str = "utf-8",
        pattern: Optional[str] = None,
        search_content: Optional[str] = None,
        is_regex: bool = False,
        case_sensitive: bool = True,
        recursive: bool = True,
        include_hidden: bool = False,
        max_results: int = 100,
        max_size_bytes: Optional[int] = None,
        atomic: bool = True,
        create_parents: bool = True,
        overwrite: bool = False,
        dry_run: bool = False,
        redaction_enabled: bool = True,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        target_content: Optional[str] = None,
        replacement: Optional[str] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> FileResult:
        """Execute sandboxed filesystem operations using the registered FilePlugin."""
        op_enum = FileOperation(operation) if isinstance(operation, str) else operation
        file_input = FileInput(
            operation=op_enum,
            path=path,
            destination_path=destination_path,
            content=content,
            encoding=encoding,
            pattern=pattern,
            search_content=search_content,
            is_regex=is_regex,
            case_sensitive=case_sensitive,
            recursive=recursive,
            include_hidden=include_hidden,
            max_results=max_results,
            max_size_bytes=max_size_bytes,
            atomic=atomic,
            create_parents=create_parents,
            overwrite=overwrite,
            dry_run=dry_run,
            redaction_enabled=redaction_enabled,
            line_start=line_start,
            line_end=line_end,
            target_content=target_content,
            replacement=replacement,
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("file", file_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, FileResult):
            raise PluginExecutionError(
                f"File execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="file",
            )
        return exec_res.output

    async def afile(
        self,
        operation: Union[FileOperation, str] = FileOperation.READ,
        path: Optional[str] = None,
        destination_path: Optional[str] = None,
        content: Optional[str] = None,
        encoding: str = "utf-8",
        pattern: Optional[str] = None,
        search_content: Optional[str] = None,
        is_regex: bool = False,
        case_sensitive: bool = True,
        recursive: bool = True,
        include_hidden: bool = False,
        max_results: int = 100,
        max_size_bytes: Optional[int] = None,
        atomic: bool = True,
        create_parents: bool = True,
        overwrite: bool = False,
        dry_run: bool = False,
        redaction_enabled: bool = True,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        target_content: Optional[str] = None,
        replacement: Optional[str] = None,
        timeout: Optional[float] = 30.0,
        **kwargs: Any,
    ) -> FileResult:
        """Asynchronously execute sandboxed filesystem operations."""
        op_enum = FileOperation(operation) if isinstance(operation, str) else operation
        file_input = FileInput(
            operation=op_enum,
            path=path,
            destination_path=destination_path,
            content=content,
            encoding=encoding,
            pattern=pattern,
            search_content=search_content,
            is_regex=is_regex,
            case_sensitive=case_sensitive,
            recursive=recursive,
            include_hidden=include_hidden,
            max_results=max_results,
            max_size_bytes=max_size_bytes,
            atomic=atomic,
            create_parents=create_parents,
            overwrite=overwrite,
            dry_run=dry_run,
            redaction_enabled=redaction_enabled,
            line_start=line_start,
            line_end=line_end,
            target_content=target_content,
            replacement=replacement,
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("file", file_input, timeout=timeout)
        if not exec_res.success or not isinstance(exec_res.output, FileResult):
            raise PluginExecutionError(
                f"Async file execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="file",
            )
        return exec_res.output

    def read_file(self, path: str, encoding: str = "utf-8", **kwargs: Any) -> FileResult:
        """Convenience method to read file content."""
        return self.file(operation=FileOperation.READ, path=path, encoding=encoding, **kwargs)

    def write_file(self, path: str, content: str = "", overwrite: bool = True, **kwargs: Any) -> FileResult:
        """Convenience method to write file content."""
        return self.file(operation=FileOperation.WRITE, path=path, content=content, overwrite=overwrite, **kwargs)

    def list_files(
        self, path: Optional[str] = None, pattern: Optional[str] = None, **kwargs: Any
    ) -> List[FileItemMetadata]:
        """Convenience method to list files."""
        res = self.file(operation=FileOperation.LIST, path=path, pattern=pattern, **kwargs)
        return res.items

    # -------------------------------------------------------------------------
    # Verification Operations
    # -------------------------------------------------------------------------
    def verify(
        self,
        candidate: Any,
        operation: VerificationOperation = VerificationOperation.FINAL_RESPONSE_VERIFICATION,
        task: Optional[str] = None,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        candidates: Optional[List[CandidateItem]] = None,
        expected_format: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
        rubric: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.70,
        strict_mode: bool = False,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> VerificationResult:
        """Synchronously execute a verification quality check via VerificationPlugin."""
        verif_input = VerificationInput(
            operation=operation,
            candidate=candidate,
            task=task,
            context=context,
            evidence=evidence or [],
            candidates=candidates or [],
            expected_format=expected_format,
            schema_definition=schema_definition,
            trajectory=trajectory,
            rubric=rubric,
            confidence_threshold=confidence_threshold,
            strict_mode=strict_mode,
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("verification", verif_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, VerificationResult):
            raise PluginExecutionError(
                f"Verification execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="verification",
            )
        return exec_res.output

    async def averify(
        self,
        candidate: Any,
        operation: VerificationOperation = VerificationOperation.FINAL_RESPONSE_VERIFICATION,
        task: Optional[str] = None,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        candidates: Optional[List[CandidateItem]] = None,
        expected_format: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
        rubric: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.70,
        strict_mode: bool = False,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> VerificationResult:
        """Asynchronously execute a verification quality check via VerificationPlugin."""
        verif_input = VerificationInput(
            operation=operation,
            candidate=candidate,
            task=task,
            context=context,
            evidence=evidence or [],
            candidates=candidates or [],
            expected_format=expected_format,
            schema_definition=schema_definition,
            trajectory=trajectory,
            rubric=rubric,
            confidence_threshold=confidence_threshold,
            strict_mode=strict_mode,
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("verification", verif_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, VerificationResult):
            raise PluginExecutionError(
                f"Async verification execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="verification",
            )
        return exec_res.output

    def verify_output(
        self,
        candidate: Any,
        expected_format: Optional[str] = None,
        schema_definition: Optional[Dict[str, Any]] = None,
        strict_mode: bool = False,
        **kwargs: Any,
    ) -> VerificationResult:
        """Convenience method to validate output structural integrity or format."""
        return self.verify(
            candidate=candidate,
            operation=VerificationOperation.OUTPUT_VALIDATION,
            expected_format=expected_format,
            schema_definition=schema_definition,
            strict_mode=strict_mode,
            **kwargs,
        )

    def fact_check(
        self,
        candidate: Any,
        evidence: Optional[List[EvidenceItem]] = None,
        strict_mode: bool = False,
        **kwargs: Any,
    ) -> VerificationResult:
        """Convenience method to fact check claims against source evidence."""
        return self.verify(
            candidate=candidate,
            operation=VerificationOperation.FACT_CHECKING,
            evidence=evidence or [],
            strict_mode=strict_mode,
            **kwargs,
        )

    def rerank_candidates(
        self,
        candidates: List[CandidateItem],
        task: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        **kwargs: Any,
    ) -> List[CandidateItem]:
        """Convenience method to score and rerank candidate items."""
        res = self.verify(
            candidate=None,
            operation=VerificationOperation.RESULT_RERANKING,
            candidates=candidates,
            task=task,
            evidence=evidence,
            **kwargs,
        )
        return res.reranked_candidates or candidates

    # -------------------------------------------------------------------------
    # Experience & Feedback Operations
    # -------------------------------------------------------------------------
    def experience(
        self,
        operation: ExperienceOperation = ExperienceOperation.EXPERIENCE_RETRIEVAL,
        item: Optional[ExperienceItem] = None,
        experience_id: Optional[str] = None,
        task: Optional[str] = None,
        context: Optional[str] = None,
        plugin_name: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Any = None,
        success: Optional[bool] = None,
        verification_status: Optional[str] = None,
        verification_score: Optional[float] = None,
        user_feedback: Optional[UserFeedback] = None,
        confidence: float = 1.0,
        lesson: Optional[str] = None,
        failure_reason: Optional[str] = None,
        failure_avoidance_advice: Optional[str] = None,
        error: Optional[str] = None,
        limit: int = 5,
        filter_plugin: Optional[str] = None,
        tags: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> ExperienceResult:
        """Synchronously execute an experience operation via ExperiencePlugin."""
        exp_input = ExperienceInput(
            operation=operation,
            item=item,
            experience_id=experience_id,
            task=task,
            context=context,
            plugin_name=plugin_name,
            action=action,
            outcome=outcome,
            success=success,
            verification_status=verification_status,
            verification_score=verification_score,
            user_feedback=user_feedback,
            confidence=confidence,
            lesson=lesson,
            failure_reason=failure_reason,
            failure_avoidance_advice=failure_avoidance_advice,
            error=error,
            limit=limit,
            filter_plugin=filter_plugin,
            tags=tags or [],
            metadata=kwargs,
        )

        exec_res = self.execute_plugin("experience", exp_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, ExperienceResult):
            raise PluginExecutionError(
                f"Experience execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="experience",
            )
        return exec_res.output

    async def aexperience(
        self,
        operation: ExperienceOperation = ExperienceOperation.EXPERIENCE_RETRIEVAL,
        item: Optional[ExperienceItem] = None,
        experience_id: Optional[str] = None,
        task: Optional[str] = None,
        context: Optional[str] = None,
        plugin_name: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Any = None,
        success: Optional[bool] = None,
        verification_status: Optional[str] = None,
        verification_score: Optional[float] = None,
        user_feedback: Optional[UserFeedback] = None,
        confidence: float = 1.0,
        lesson: Optional[str] = None,
        failure_reason: Optional[str] = None,
        failure_avoidance_advice: Optional[str] = None,
        error: Optional[str] = None,
        limit: int = 5,
        filter_plugin: Optional[str] = None,
        tags: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> ExperienceResult:
        """Asynchronously execute an experience operation via ExperiencePlugin."""
        exp_input = ExperienceInput(
            operation=operation,
            item=item,
            experience_id=experience_id,
            task=task,
            context=context,
            plugin_name=plugin_name,
            action=action,
            outcome=outcome,
            success=success,
            verification_status=verification_status,
            verification_score=verification_score,
            user_feedback=user_feedback,
            confidence=confidence,
            lesson=lesson,
            failure_reason=failure_reason,
            failure_avoidance_advice=failure_avoidance_advice,
            error=error,
            limit=limit,
            filter_plugin=filter_plugin,
            tags=tags or [],
            metadata=kwargs,
        )

        exec_res = await self.aexecute_plugin("experience", exp_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, ExperienceResult):
            raise PluginExecutionError(
                f"Async experience execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="experience",
            )
        return exec_res.output

    def record_experience(
        self,
        task: str,
        context: Optional[str] = None,
        plugin_name: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Any = None,
        success: bool = True,
        verification_status: Optional[str] = None,
        verification_score: Optional[float] = None,
        confidence: float = 1.0,
        lesson: Optional[str] = None,
        failure_reason: Optional[str] = None,
        failure_avoidance_advice: Optional[str] = None,
        error: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ExperienceResult:
        """Convenience method to record execution results into experience memory."""
        item = ExperienceItem(
            task=task,
            context=context,
            selected_plugin=plugin_name,
            action=action,
            outcome=outcome,
            success=success,
            verification_status=verification_status,
            verification_score=verification_score,
            confidence=confidence,
            lesson=lesson,
            failure_reason=failure_reason,
            failure_avoidance_advice=failure_avoidance_advice,
            error=error,
            tags=tags or [],
            metadata=kwargs,
        )
        return self.experience(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            item=item,
        )

    def retrieve_experiences(
        self,
        task: Optional[str] = None,
        filter_plugin: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 5,
        **kwargs: Any,
    ) -> List[ExperienceItem]:
        """Convenience method to query and rank relevant experiences."""
        res = self.experience(
            operation=ExperienceOperation.EXPERIENCE_RETRIEVAL,
            task=task,
            filter_plugin=filter_plugin,
            success=success,
            limit=limit,
            **kwargs,
        )
        return res.experiences

    def get_decision_context(self, task: str, limit: int = 3) -> Optional[str]:
        """Convenience method to retrieve decision context (lessons and warnings) for Core LLM prompts."""
        res = self.experience(
            operation=ExperienceOperation.EXPERIENCE_RETRIEVAL,
            task=task,
            limit=limit,
        )
        return res.decision_context

    def add_experience_feedback(
        self,
        experience_id: str,
        rating: Optional[int] = None,
        thumbs_up: Optional[bool] = None,
        comments: Optional[str] = None,
        corrected_outcome: Optional[str] = None,
        **kwargs: Any,
    ) -> ExperienceResult:
        """Convenience method to attach user feedback to an experience."""
        fb = UserFeedback(
            rating=rating,
            thumbs_up=thumbs_up,
            comments=comments,
            corrected_outcome=corrected_outcome,
        )
        return self.experience(
            operation=ExperienceOperation.USER_FEEDBACK,
            experience_id=experience_id,
            user_feedback=fb,
            **kwargs,
        )

    def get_failure_warnings(
        self, task: str, limit: int = 5, plugin: Optional[str] = None
    ) -> List[FailureWarning]:
        """Convenience method to query failure avoidance warnings."""
        res = self.experience(
            operation=ExperienceOperation.FAILURE_AVOIDANCE,
            task=task,
            filter_plugin=plugin,
            limit=limit,
        )
        return res.failure_warnings

    # -------------------------------------------------------------------------
    # Automation & Multi-Step Task Operations (Plugin #9)
    # -------------------------------------------------------------------------
    def automate(
        self,
        operation: AutomationOperation,
        task_id: Optional[str] = None,
        objective: Optional[str] = None,
        steps: Optional[List[TaskStep]] = None,
        plan: Optional[TaskPlan] = None,
        step_id: Optional[str] = None,
        auto_plan: bool = True,
        max_steps: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        limit: int = 50,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> AutomationResult:
        """Synchronously execute an automation task operation via AutomationPlugin."""
        auto_input = AutomationInput(
            operation=operation,
            task_id=task_id,
            objective=objective,
            steps=steps or [],
            plan=plan,
            step_id=step_id,
            auto_plan=auto_plan,
            max_steps=max_steps,
            timeout_seconds=timeout_seconds,
            limit=limit,
            metadata=metadata or {},
        )
        exec_res = self.execute_plugin("automation", auto_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, AutomationResult):
            raise PluginExecutionError(
                f"Automation execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="automation",
            )
        return exec_res.output

    async def aautomate(
        self,
        operation: AutomationOperation,
        task_id: Optional[str] = None,
        objective: Optional[str] = None,
        steps: Optional[List[TaskStep]] = None,
        plan: Optional[TaskPlan] = None,
        step_id: Optional[str] = None,
        auto_plan: bool = True,
        max_steps: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        limit: int = 50,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> AutomationResult:
        """Asynchronously execute an automation task operation via AutomationPlugin."""
        auto_input = AutomationInput(
            operation=operation,
            task_id=task_id,
            objective=objective,
            steps=steps or [],
            plan=plan,
            step_id=step_id,
            auto_plan=auto_plan,
            max_steps=max_steps,
            timeout_seconds=timeout_seconds,
            limit=limit,
            metadata=metadata or {},
        )
        exec_res = await self.aexecute_plugin("automation", auto_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, AutomationResult):
            raise PluginExecutionError(
                f"Async automation execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="automation",
            )
        return exec_res.output

    def create_task(
        self,
        objective: str,
        steps: Optional[List[TaskStep]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> AutomationResult:
        """Convenience method to create a structured task."""
        return self.automate(
            operation=AutomationOperation.TASK_CREATE,
            objective=objective,
            steps=steps,
            task_id=task_id,
            metadata=metadata,
            auto_plan=auto_plan,
        )

    def plan_task(
        self,
        objective: Optional[str] = None,
        steps: Optional[List[TaskStep]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AutomationResult:
        """Convenience method to plan and validate DAG dependencies for a task."""
        return self.automate(
            operation=AutomationOperation.TASK_PLAN,
            objective=objective,
            steps=steps,
            task_id=task_id,
            metadata=metadata,
        )

    def execute_task(
        self,
        task_id: Optional[str] = None,
        plan: Optional[TaskPlan] = None,
        timeout_seconds: Optional[float] = None,
        max_steps: Optional[int] = None,
    ) -> AutomationResult:
        """Convenience method to synchronously execute a planned task DAG."""
        return self.automate(
            operation=AutomationOperation.TASK_EXECUTE,
            task_id=task_id,
            plan=plan,
            timeout_seconds=timeout_seconds,
            max_steps=max_steps,
        )

    async def aexecute_task(
        self,
        task_id: Optional[str] = None,
        plan: Optional[TaskPlan] = None,
        timeout_seconds: Optional[float] = None,
        max_steps: Optional[int] = None,
    ) -> AutomationResult:
        """Convenience method to asynchronously execute a planned task DAG."""
        return await self.aautomate(
            operation=AutomationOperation.TASK_EXECUTE,
            task_id=task_id,
            plan=plan,
            timeout_seconds=timeout_seconds,
            max_steps=max_steps,
        )

    def pause_task(self, task_id: str, reason: Optional[str] = None) -> AutomationResult:
        """Convenience method to request pausing an active task."""
        return self.automate(
            operation=AutomationOperation.TASK_PAUSE,
            task_id=task_id,
            metadata={"reason": reason} if reason else {},
        )

    def resume_task(self, task_id: str, timeout_seconds: Optional[float] = None) -> AutomationResult:
        """Convenience method to resume a paused task."""
        return self.automate(
            operation=AutomationOperation.TASK_RESUME,
            task_id=task_id,
            timeout_seconds=timeout_seconds,
        )

    async def aresume_task(self, task_id: str, timeout_seconds: Optional[float] = None) -> AutomationResult:
        """Convenience method to asynchronously resume a paused task."""
        return await self.aautomate(
            operation=AutomationOperation.TASK_RESUME,
            task_id=task_id,
            timeout_seconds=timeout_seconds,
        )

    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> AutomationResult:
        """Convenience method to cancel an active task."""
        return self.automate(
            operation=AutomationOperation.TASK_CANCEL,
            task_id=task_id,
            metadata={"reason": reason} if reason else {},
        )

    def get_task_status(self, task_id: str) -> AutomationResult:
        """Convenience method to inspect current task status and step run records."""
        return self.automate(
            operation=AutomationOperation.TASK_STATUS,
            task_id=task_id,
        )

    def retry_task(
        self,
        task_id: str,
        step_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> AutomationResult:
        """Convenience method to retry a failed task or failed step."""
        return self.automate(
            operation=AutomationOperation.TASK_RETRY,
            task_id=task_id,
            step_id=step_id,
            timeout_seconds=timeout_seconds,
        )

    async def aretry_task(
        self,
        task_id: str,
        step_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> AutomationResult:
        """Convenience method to asynchronously retry a failed task or failed step."""
        return await self.aautomate(
            operation=AutomationOperation.TASK_RETRY,
            task_id=task_id,
            step_id=step_id,
            timeout_seconds=timeout_seconds,
        )

    def get_task_history(self, task_id: Optional[str] = None, limit: int = 50) -> AutomationResult:
        """Convenience method to retrieve task execution audit trail."""
        return self.automate(
            operation=AutomationOperation.TASK_HISTORY,
            task_id=task_id,
            limit=limit,
        )

    def record_automation_outcome(
        self,
        automation_result: AutomationResult,
        task_description: Optional[str] = None,
        verification_status: Optional[str] = None,
        verification_score: Optional[float] = None,
        lesson: Optional[str] = None,
        failure_reason: Optional[str] = None,
        failure_avoidance_advice: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ExperienceResult:
        """
        Record the structured outcome of an automation task into Experience Plugin #8.
        Connects Automation task execution to Xeren's experience and learning loop.
        """
        task_desc = task_description or (
            automation_result.plan.objective
            if automation_result.plan
            else (automation_result.task_id or "automation_task")
        )
        outcome = automation_result.to_experience_payload()

        if not automation_result.success and not failure_reason:
            if automation_result.step_errors:
                failed_items = [f"Step '{s}': {err}" for s, err in automation_result.step_errors.items()]
                failure_reason = f"Automation step failure(s): {'; '.join(failed_items)}"
            else:
                failure_reason = automation_result.error or "Automation task failed"

        return self.record_experience(
            task=task_desc,
            context=f"Automation task {automation_result.task_id or 'unknown'} with {len(automation_result.completed_steps)} completed and {len(automation_result.failed_steps)} failed steps.",
            plugin_name="automation",
            action=automation_result.operation.value,
            outcome=outcome,
            success=automation_result.success,
            verification_status=verification_status,
            verification_score=verification_score,
            confidence=1.0 if automation_result.success else 0.5,
            lesson=lesson,
            failure_reason=failure_reason,
            failure_avoidance_advice=failure_avoidance_advice,
            error=automation_result.error
            or ("; ".join(automation_result.step_errors.values()) if automation_result.step_errors else None),
            tags=(tags or []) + ["automation"],
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # API & External Communication Operations (Plugin #10)
    # -------------------------------------------------------------------------
    def api(
        self,
        operation: ApiOperation = ApiOperation.API_REQUEST,
        request: Optional[ApiRequest] = None,
        api_key: Optional[str] = None,
        key_id: Optional[str] = None,
        create_request: Optional[ApiKeyCreateRequest] = None,
        rotate_request: Optional[ApiKeyRotateRequest] = None,
        revoke_request: Optional[ApiKeyRevokeRequest] = None,
        scope_to_check: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        client_ip: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> ApiResult:
        """Synchronously execute an API gateway operation via ApiPlugin."""
        api_input = ApiInput(
            operation=operation,
            request=request,
            api_key=api_key,
            key_id=key_id,
            create_request=create_request,
            rotate_request=rotate_request,
            revoke_request=revoke_request,
            scope_to_check=scope_to_check,
            endpoint=endpoint,
            method=method,
            body=body,
            headers=headers,
            client_ip=client_ip,
            metadata=kwargs,
        )
        exec_res = self.execute_plugin("api", api_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, ApiResult):
            raise PluginExecutionError(
                f"Api execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="api",
            )
        return exec_res.output

    async def aapi(
        self,
        operation: ApiOperation = ApiOperation.API_REQUEST,
        request: Optional[ApiRequest] = None,
        api_key: Optional[str] = None,
        key_id: Optional[str] = None,
        create_request: Optional[ApiKeyCreateRequest] = None,
        rotate_request: Optional[ApiKeyRotateRequest] = None,
        revoke_request: Optional[ApiKeyRevokeRequest] = None,
        scope_to_check: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        client_ip: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> ApiResult:
        """Asynchronously execute an API gateway operation via ApiPlugin."""
        api_input = ApiInput(
            operation=operation,
            request=request,
            api_key=api_key,
            key_id=key_id,
            create_request=create_request,
            rotate_request=rotate_request,
            revoke_request=revoke_request,
            scope_to_check=scope_to_check,
            endpoint=endpoint,
            method=method,
            body=body,
            headers=headers,
            client_ip=client_ip,
            metadata=kwargs,
        )
        exec_res = await self.aexecute_plugin("api", api_input, timeout=timeout)
        if not exec_res.output or not isinstance(exec_res.output, ApiResult):
            raise PluginExecutionError(
                f"Async api execution failed: {exec_res.error or 'Unknown error'}",
                plugin_name="api",
            )
        return exec_res.output

    def handle_api_request(self, request: ApiRequest) -> ApiResponse:
        """Convenience method to process an API request through the gateway."""
        res = self.api(operation=ApiOperation.API_REQUEST, request=request)
        if res.response:
            return res.response
        return ApiResponse(
            request_id=request.request_id,
            status_code=500,
            success=False,
            error=ApiError(code="INTERNAL_ERROR", message=res.error or "Execution error"),
        )

    async def ahandle_api_request(self, request: ApiRequest) -> ApiResponse:
        """Convenience method to asynchronously process an API request."""
        res = await self.aapi(operation=ApiOperation.API_REQUEST, request=request)
        if res.response:
            return res.response
        return ApiResponse(
            request_id=request.request_id,
            status_code=500,
            success=False,
            error=ApiError(code="INTERNAL_ERROR", message=res.error or "Execution error"),
        )

    def create_api_key(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        rate_limit_per_minute: int = 60,
        expires_in_days: Optional[int] = None,
        environment: ApiKeyEnvironment = ApiKeyEnvironment.LIVE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApiKeyCreatedResponse:
        """Convenience method to generate and persist a new Xeren API key."""
        api_p = self.plugin_manager.get("api")
        if isinstance(api_p, ApiPlugin):
            return api_p.create_api_key(
                name=name,
                scopes=scopes,
                rate_limit_per_minute=rate_limit_per_minute,
                expires_in_days=expires_in_days,
                environment=environment,
                metadata=metadata,
            )
        req = ApiKeyCreateRequest(
            name=name,
            scopes=scopes or ["*"],
            rate_limit_per_minute=rate_limit_per_minute,
            expires_in_days=expires_in_days,
            environment=environment,
            metadata=metadata or {},
        )
        res = self.api(operation=ApiOperation.API_KEY_AUTHENTICATION, create_request=req)
        if res.created_key:
            return res.created_key
        raise RuntimeError("Failed to create API key.")

    def validate_api_key(self, api_key: str) -> ApiResult:
        """Convenience method to authenticate an API key."""
        return self.api(operation=ApiOperation.API_KEY_AUTHENTICATION, api_key=api_key)

    def rotate_api_key(self, key_id: str, grace_period_seconds: float = 0.0) -> ApiResult:
        """Convenience method to rotate an active API key."""
        return self.api(
            operation=ApiOperation.API_KEY_ROTATION,
            key_id=key_id,
            rotate_request=ApiKeyRotateRequest(key_id=key_id, grace_period_seconds=grace_period_seconds),
        )

    def revoke_api_key(self, key_id: str, reason: Optional[str] = None) -> ApiResult:
        """Convenience method to revoke an API key."""
        return self.api(
            operation=ApiOperation.API_KEY_REVOCATION,
            key_id=key_id,
            revoke_request=ApiKeyRevokeRequest(key_id=key_id, reason=reason),
 main
        )

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
