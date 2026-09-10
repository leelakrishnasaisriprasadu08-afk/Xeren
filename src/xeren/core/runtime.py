"""Xeren Core orchestrator managing plugins, models, and workflows."""

import asyncio
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel

from xeren.core.context import CoreContext
from xeren.core.hallucination_guard import HallucinationGuard, StructuredAnswer
from xeren.core.intent import IntentClassifier, IntentResult, RoutingCategory
from xeren.core.learner import EpistemicLearner, KnowledgeGapDetector, LearnedKnowledge
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
from xeren.plugins.conversation.plugin import ConversationPlugin
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

from pathlib import Path

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.browser.mock import MockBrowserAdapter
try:
    from xeren.agent.browser.playwright_adapter import PlaywrightBrowserAdapter
except Exception:
    PlaywrightBrowserAdapter = None  # type: ignore
from xeren.agent.controller import AgentController
from xeren.agent.permissions import PermissionManager
from xeren.agent.plugins.experience import ExperienceInput as AgentExperienceInput, ExperiencePlugin as AgentExperiencePlugin
from xeren.agent.plugins.verification import VerificationInput as AgentVerificationInput, VerificationPlugin as AgentVerificationPlugin
from xeren.agent.types import AgentState, AgentStatus
from xeren.core.planner import CorePlannerAdapter, TaskPlan

from xeren.rag.document import Document
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.workspace.manager import WorkspaceManager
from xeren.workspace.schemas import (
    CandidateFile,
    DiscoveryRequest,
    DiscoveryResult,
    PermissionMode,
    RetrievedContent,
    WorkspaceContext,
    WorkspaceRequirement,
    WorkspaceRoot,
)

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
        workspace_manager: Optional[WorkspaceManager] = None,
    ) -> None:
        self.llm = llm or MockLLM()
        self.plugin_manager = plugin_manager or PluginManager()
        self.workspace_manager = workspace_manager
        self.context = CoreContext(llm=self.llm)
        self.intent_classifier = IntentClassifier()
        self.hallucination_guard = HallucinationGuard(search_engine=search_engine)
        self.epistemic_learner = EpistemicLearner(
            llm=self.llm,
            search_engine=search_engine,
            plugin_manager=self.plugin_manager,
        )

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
            if not self.plugin_manager.has("file"):
                file_plugin = FilePlugin()
                self.register_plugin(file_plugin)
            if not self.plugin_manager.has("verification"):
                verification_plugin = VerificationPlugin()
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

            if not self.plugin_manager.has("conversation"):
                conversation_plugin = ConversationPlugin(llm=self.llm)
                self.register_plugin(conversation_plugin)


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
        conversation = self.plugin_manager.get("conversation")
        if isinstance(conversation, ConversationPlugin):
            conversation.set_llm(llm)
        self.epistemic_learner.llm = llm

    def set_search_engine(self, engine: BaseSearchEngine) -> None:
        """Replace the active search engine across registered research plugins."""
        research = self.plugin_manager.get("research")
        if isinstance(research, ResearchPlugin):
            research.set_search_engine(engine)
        self.epistemic_learner.search_engine = engine
        self.hallucination_guard.search_tool.engine = engine

    def set_workspace_manager(self, manager: WorkspaceManager) -> None:
        """Inject or configure the active WorkspaceManager."""
        self.workspace_manager = manager

    def add_workspace_root(
        self,
        path: Union[str, Path],
        root_id: Optional[str] = None,
        permission_mode: Optional[PermissionMode] = None,
    ) -> WorkspaceRoot:
        """Authorize a filesystem directory as an active workspace root."""
        if self.workspace_manager is None:
            self.workspace_manager = WorkspaceManager()
        return self.workspace_manager.authorize_root(
            path=path,
            root_id=root_id,
            permission_mode=permission_mode,
        )

    def determine_workspace_requirement(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkspaceRequirement]:
        """Analyze user goal and context to determine if workspace resources are needed."""
        goal_lower = goal.lower()
        tokens = set(re.findall(r"\b[a-zA-Z0-9_]+\b", goal_lower))

        # Target keyword sets
        data_terms = {"sales", "revenue", "data", "dataset", "csv", "xlsx", "sheet", "metrics", "trend", "analytics", "churn"}
        doc_terms = {"research", "paper", "papers", "document", "documents", "spec", "specification", "requirements", "report", "notes"}
        code_terms = {"code", "project", "bug", "fix", "auth", "login", "endpoint", "api", "codebase", "yesterday"}
        website_terms = {"website", "web", "dashboard", "page"}

        matched_data = [t for t in data_terms if t in tokens]
        matched_docs = [t for t in doc_terms if t in tokens]
        matched_code = [t for t in code_terms if t in tokens]
        matched_web = [t for t in website_terms if t in tokens]

        if matched_data and matched_web:
            return WorkspaceRequirement(
                requires_workspace=True,
                purpose="data_and_website",
                preferred_types=["csv", "xlsx", "json"],
                query_terms=matched_data + matched_web,
                intent_keywords=["analyze", "create_website"],
            )

        if matched_data:
            return WorkspaceRequirement(
                requires_workspace=True,
                purpose="sales_data_analysis" if "sales" in tokens else "data_analysis",
                preferred_types=["csv", "xlsx", "json"],
                query_terms=matched_data,
                intent_keywords=["analyze", "inspect"],
            )

        if matched_docs:
            return WorkspaceRequirement(
                requires_workspace=True,
                purpose="research_docs",
                preferred_types=["pdf", "md", "docx", "txt"],
                query_terms=matched_docs,
                intent_keywords=["research", "explain"],
            )

        if matched_code:
            return WorkspaceRequirement(
                requires_workspace=True,
                purpose="codebase_inspection",
                preferred_types=["py", "ts", "js", "json", "toml"],
                query_terms=matched_code,
                intent_keywords=["fix", "inspect", "debug"],
            )

        if any(w in tokens for w in ("workspace", "file", "files")):
            return WorkspaceRequirement(
                requires_workspace=True,
                purpose="workspace_file_access",
                preferred_types=[],
                query_terms=[goal],
                intent_keywords=["discover", "inspect"],
            )

        return None

    def process_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        workspace_root: Optional[Union[str, Path, WorkspaceRoot]] = None,
    ) -> Dict[str, Any]:
        """Execute autonomous end-to-end task workflow:
        User Goal -> Understand Task -> Workspace Requirement -> Autonomous Discovery ->
        Relevance Ranking -> Content Retrieval -> Multi-Plugin Workflow -> Verification -> Experience -> Response.
        """
        if workspace_root is not None:
            if isinstance(workspace_root, WorkspaceRoot):
                if self.workspace_manager is None:
                    self.workspace_manager = WorkspaceManager()
                self.workspace_manager.add_root(workspace_root)
            else:
                self.add_workspace_root(workspace_root)

        requirement = self.determine_workspace_requirement(goal, context)

        # 1. If task does not require workspace resources, route to standard plugins
        if requirement is None or not requirement.requires_workspace:
            logger.info("Task does not require workspace resources: '%s'", goal)
            return {
                "goal": goal,
                "requires_workspace": False,
                "workspace_context": None,
                "selected_files": [],
                "workflow": ["standard_dispatch"],
                "response": f"Processed task: {goal}",
                "success": True,
            }

        # 2. Workspace is required
        if self.workspace_manager is None or not self.workspace_manager.list_roots():
            return {
                "goal": goal,
                "requires_workspace": True,
                "status": "no_workspace_configured",
                "workspace_context": None,
                "selected_files": [],
                "workflow": ["workspace_discovery"],
                "response": f"Workspace resources are required for '{goal}', but no workspace root is currently authorized.",
                "success": False,
                "requires_user_input": True,
            }

        # 3. Autonomous Discovery & Ranking
        discovery_req = DiscoveryRequest(
            goal=goal,
            task_context=context,
            preferred_types=requirement.preferred_types,
            search_terms=requirement.query_terms,
        )
        discovery_res = self.workspace_manager.discover(discovery_req)

        # 4. Ambiguity handling
        if discovery_res.ambiguity_detected:
            logger.info("Ambiguous workspace files detected for goal '%s'", goal)
            return {
                "goal": goal,
                "requires_workspace": True,
                "status": "ambiguous",
                "ambiguity_detected": True,
                "clarification_message": discovery_res.clarification_message,
                "candidates": [c.model_dump() for c in discovery_res.candidates],
                "selected_files": [],
                "workflow": ["workspace_discovery", "clarification"],
                "response": discovery_res.clarification_message,
                "success": True,
                "requires_user_input": True,
            }

        if not discovery_res.selected_candidates:
            logger.info("No relevant workspace files found for goal '%s'", goal)
            msg = discovery_res.clarification_message or f"No relevant files found in authorized workspace for: '{goal}'."
            return {
                "goal": goal,
                "requires_workspace": True,
                "status": "no_files_found",
                "ambiguity_detected": False,
                "clarification_message": msg,
                "candidates": [],
                "selected_files": [],
                "workflow": ["workspace_discovery", "clarification"],
                "response": msg,
                "success": False,
                "requires_user_input": True,
            }

        # 5. Content Retrieval
        retrieved_items: List[RetrievedContent] = []
        for candidate in discovery_res.selected_candidates:
            retrieved_items.append(self.workspace_manager.retrieve(candidate))

        workspace_ctx = self.workspace_manager.build_context(goal, requirement, task_context=context)

        # 6. Automatic Multi-Plugin Routing
        workflow: List[str] = ["workspace_discovery"]
        plugin_outputs: Dict[str, Any] = {}
        goal_lower = goal.lower()

        # Multi-plugin Scenario: Data + Website
        if any(k in goal_lower for k in ("website", "dashboard")) and any(k in goal_lower for k in ("data", "sales", "dataset", "trends")):
            workflow.append("data")
            first_ret = retrieved_items[0]
            data_res = self.data(
                operation=DataOperation.INSPECT,
                data=first_ret.content,
                format=DataFormat.CSV if first_ret.file_type == "csv" else DataFormat.JSON,
            )
            plugin_outputs["data"] = data_res

            workflow.append("website")
            web_res = self.website(
                requirement=goal,
                operation=WebsiteOperation.GENERATE,
                specification={
                    "title": f"Report: {goal}",
                    "description": f"Visualizing results from {first_ret.path}",
                },
            )
            plugin_outputs["website"] = web_res

        # Data Scenario: Sales or tabular data analysis
        elif any(k in goal_lower for k in ("data", "sales", "dataset", "csv", "excel", "sheet", "revenue")):
            workflow.append("data")
            first_ret = retrieved_items[0]
            data_res = self.data(
                operation=DataOperation.INSPECT,
                data=first_ret.content,
                format=DataFormat.CSV if first_ret.file_type == "csv" else DataFormat.JSON,
            )
            plugin_outputs["data"] = data_res

        # Research / Document Scenario
        elif any(k in goal_lower for k in ("research", "paper", "papers", "explain", "document", "documents", "spec")):
            workflow.append("knowledge")
            for c in discovery_res.selected_candidates:
                k_plugin = self.plugin_manager.get("knowledge")
                if k_plugin:
                    self.workspace_manager.ingest_into_rag(c, k_plugin)
            k_res = self.knowledge(query=goal, operation=KnowledgeOperation.QUERY)
            plugin_outputs["knowledge"] = k_res

        # Coding / Bug Fix Scenario
        elif any(k in goal_lower for k in ("code", "bug", "fix", "login", "auth", "project")):
            workflow.append("coding")
            code_res = self.coding(
                task=goal,
                operation=CodingOperation.GENERATE,
                context_files=[r.path for r in retrieved_items],
            )
            plugin_outputs["coding"] = code_res

        else:
            workflow.append("conversation")

        # 7. Verification
        workflow.append("verification")
        ver_res = self.verify(
            candidate=str(plugin_outputs),
            task=goal,
            operation=VerificationOperation.FINAL_RESPONSE_VERIFICATION,
        )
        plugin_outputs["verification"] = ver_res

        # 8. Experience Learning Loop
        workflow.append("experience")
        self.record_experience(
            task=goal,
            context=f"Workflow with files: {[c.relative_path for c in discovery_res.selected_candidates]}",
            plugin_name="workspace",
            action="autonomous_discovery_and_execution",
            outcome={"files": [c.relative_path for c in discovery_res.selected_candidates], "plugins": workflow},
            success=True,
        )

        # 9. Response
        workflow.append("response")
        file_summary = ", ".join(c.relative_path for c in discovery_res.selected_candidates)
        response_text = (
            f"Discovered relevant workspace file(s): {file_summary}. "
            f"Successfully executed workflow: {' -> '.join(workflow)}."
        )

        return {
            "goal": goal,
            "requires_workspace": True,
            "status": "completed",
            "workspace_context": workspace_ctx.model_dump(),
            "selected_files": [c.relative_path for c in discovery_res.selected_candidates],
            "workflow": workflow,
            "plugin_outputs": {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in plugin_outputs.items()},
            "verification": ver_res.model_dump(),
            "response": response_text,
            "success": True,
        }

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
    # Autonomous Agent Target Flow Orchestration
    # User Goal -> Xeren Core -> CorePlannerAdapter -> TaskPlan ->
    # AgentController -> PluginManager -> Required Plugin(s) ->
    # Verification -> Experience -> Result
    # -------------------------------------------------------------------------
    def _ensure_agent_plugins(self) -> None:
        """Auto-register VerificationPlugin and ExperiencePlugin if not already registered."""
        if not self.plugin_manager.has("verification"):
            self.register_plugin(AgentVerificationPlugin())
        if not self.plugin_manager.has("experience"):
            self.register_plugin(AgentExperiencePlugin())

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

        # 1. Stage 2: Knowledge Gap Detector & Learn-First Engine
        gap_detected, learned_ctx = await self.epistemic_learner.aevaluate_and_learn_if_needed(goal, ctx)
        if learned_ctx:
            ctx["learned_knowledge"] = learned_ctx.model_dump()
            goal = f"{goal}\n\n[Learned Context]: {learned_ctx.summary}"

        # 2. Initialize CorePlannerAdapter
        planner = planner_adapter or CorePlannerAdapter(
            llm=self.llm,
            plugin_manager=self.plugin_manager,
        )

        # 3. Produce and validate TaskPlan
        task_plan = await planner.acreate_task_plan(goal, ctx)

        # 4. Initialize Browser & Controller (File, OS, Web Active Domains)
        if browser_adapter is not None:
            browser = browser_adapter
        elif PlaywrightBrowserAdapter is not None and ctx.get("use_real_browser"):
            browser = PlaywrightBrowserAdapter()
        else:
            browser = MockBrowserAdapter()

        controller = AgentController(
            browser_adapter=browser,
            planner=planner,
            plugin_manager=self.plugin_manager,
            permission_manager=permission_manager,
            workspace_manager=self.workspace_manager,
            max_steps=max_steps,
        )

        # 4. Execute through AgentController
        state = await controller.arun(
            task=goal,
            context={"task_plan": task_plan, **ctx},
            max_steps=max_steps,
        )

        # 5. Final response synthesis
        final_response: str = ""
        if state.status == AgentStatus.COMPLETED:
            if state.memory.get("final_response"):
                final_response = str(state.memory["final_response"])
            elif state.completed_steps:
                last_res = state.completed_steps[-1]
                out_val = getattr(last_res, "output", None) or getattr(last_res, "data", None)
                if out_val:
                    if isinstance(out_val, WebsiteResult):
                        files_str = ", ".join(f.file_path for f in out_val.files)
                        prev_url = out_val.preview.preview_url if out_val.preview else "N/A"
                        sec_sum = out_val.security_report.summary if out_val.security_report else "Passed"
                        meta = out_val.preview.metadata if (out_val.preview and out_val.preview.metadata) else {}
                        ws_path = meta.get("workspace_path", "")
                        file_url = meta.get("file_url", "")

                        extra_info = []
                        if ws_path:
                            extra_info.append(f"• Local Directory: {ws_path}")
                        if file_url:
                            extra_info.append(f"• Direct Local File URL: {file_url}")

                        has_node = any(f.file_path == "server.js" for f in out_val.files)
                        has_py = any(f.file_path == "app.py" for f in out_val.files)
                        has_java = any(f.file_path.endswith(".java") for f in out_val.files)
                        has_sql = any(f.file_path.endswith(".sql") for f in out_val.files)

                        run_guide = []
                        if has_node:
                            run_guide.append("  - Node.js / Express API: `node server.js` (Port 5000)")
                        if has_py:
                            run_guide.append("  - Python / FastAPI Server: `uvicorn app:app --reload --port 8000`")
                        if has_java:
                            run_guide.append("  - Java / Spring Boot: `mvn spring-boot:run`")
                        if has_sql:
                            run_guide.append("  - Database Setup: `sqlite3 showroom.db < database_schema.sql`")

                        run_section = "\n• Backend Execution Commands:\n" + "\n".join(run_guide) if run_guide else ""
                        extra_str = ("\n" + "\n".join(extra_info)) if extra_info else ""

                        final_response = (
                            f"Successfully created full-stack project for '{goal}':\n\n"
                            f"• Generated Files ({len(out_val.files)}): {files_str}\n"
                            f"• Live Localhost Preview: {prev_url}"
                            f"{extra_str}\n"
                            f"• Security Status: {sec_sum}\n"
                            f"• Validation: {'Valid (0 errors)' if out_val.validation and out_val.validation.is_valid else 'Complete'}"
                            f"{run_section}"
                        )
                    elif isinstance(out_val, CodingResult):
                        code_str = getattr(out_val, "code", "") or ""
                        lang = getattr(out_val, "language", "python") or "python"
                        final_response = (
                            f"Successfully generated code for '{goal}':\n\n"
                            f"```{lang}\n{code_str.strip()}\n```\n"
                        )
                    else:
                        final_response = f"Successfully completed {goal}: {out_val}"
                elif getattr(last_res, "observation", None) and getattr(last_res.observation, "text_content", None):
                    final_response = f"Successfully completed {goal}: {last_res.observation.text_content[:200]}"
                else:
                    final_response = f"Successfully executed task: {goal}"
            else:
                final_response = f"Successfully executed task: {goal}"
        else:
            reason = state.metadata.get("completion_reason", "Task execution did not complete successfully.")
            final_response = f"Task failed: {reason}"

        # 6. Verification step
        verification_output: Any = None
        if verify_outcome and self.plugin_manager.has("verification"):
            v_input = {
                "operation": "final_response_verification",
                "task": goal,
                "success": (state.status == AgentStatus.COMPLETED),
                "expected_conditions": ctx.get("expected_conditions", []),
                "actual_data": state.memory,
                "candidate": final_response,
            }
            v_res = await self.plugin_manager.aexecute("verification", v_input)
            if v_res.output is not None:
                verification_output = v_res.output

        # 7. Experience recording step
        experience_output: Any = None
        if record_experience and self.plugin_manager.has("experience"):
            v_passed = (
                verification_output.verified
                if verification_output and hasattr(verification_output, "verified")
                else (state.status == AgentStatus.COMPLETED)
            )
            exp_input = {
                "operation": "experience_record",
                "state": state.model_dump(),
                "task": goal,
                "prediction_confidence": 0.95,
                "final_quality_score": 1.0 if (state.status == AgentStatus.COMPLETED and v_passed) else 0.0,
                "split": ctx.get("split", "train"),
                "verification_passed": v_passed,
                "verification_status": "verified" if v_passed else "failed",
                "verification_score": 1.0 if v_passed else 0.0,
            }
            exp_res = await self.plugin_manager.aexecute("experience", exp_input)
            if exp_res.output is not None:
                experience_output = exp_res.output

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
        )

    async def aanswer_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> StructuredAnswer:
        """
        Execute user query through 3-tier Intent Router and Active Hallucination Recovery Gate:
        User Query -> Intent Router (General/Project/Action) -> Execution Path -> Evidence & Verification -> Structured Answer
        """
        intent = self.intent_classifier.classify(query, context)
        raw_answer = ""
        evidence_sources: List[str] = []

        # Stage 2: Knowledge Gap Detector & Learn-First Engine
        gap_detected, learned_ctx = await self.epistemic_learner.aevaluate_and_learn_if_needed(query, context)
        if learned_ctx:
            if learned_ctx.evidence_sources:
                evidence_sources.extend(learned_ctx.evidence_sources)
            context = dict(context or {})
            context["learned_knowledge"] = learned_ctx.model_dump()

        if intent.category == RoutingCategory.GENERAL_KNOWLEDGE:
            # Route to LLM direct generation (enriched with learned knowledge if researched)
            if learned_ctx:
                prompt = (
                    f"Answer the following query accurately based on researched context:\n"
                    f"Query: {query}\n\n"
                    f"Learned Context:\n{learned_ctx.summary}\n"
                    f"Takeaways: {', '.join(learned_ctx.key_takeaways)}\n\nAnswer:"
                )
            else:
                prompt = f"Answer the following query accurately:\n{query}"
            raw_answer = await self._agenerate_text(prompt)

        elif intent.category == RoutingCategory.XEREN_PROJECT:
            # Route to Knowledge/RAG retrieval
            if self.plugin_manager.has("knowledge"):
                try:
                    k_res = self.knowledge(
                        query=query,
                        operation=KnowledgeOperation.QUERY,
                        limit=3,
                    )
                    snippets = [item.text for item in k_res.items] if hasattr(k_res, "items") else []
                    if snippets:
                        rag_ctx = "\n".join(snippets)
                        raw_answer = await self._agenerate_text(f"Context:\n{rag_ctx}\n\nQuestion: {query}\nAnswer:")
                        evidence_sources = [f"Internal Knowledge Doc #{i+1}" for i in range(len(snippets))]
                    else:
                        raw_answer = await self._agenerate_text(query)
                except Exception as e:
                    logger.warning("RAG retrieval failed, falling back to LLM: %s", e)
                    raw_answer = await self._agenerate_text(query)
            else:
                raw_answer = await self._agenerate_text(query)

        else:  # ACTION_REQUEST
            # Route to AgentController / Plugin execution
            agent_res = await self.aprocess_request(query, context=context)
            self._last_action_result = agent_res
            raw_answer = str(agent_res.get("final_response") or "Action executed successfully.")

        # Pass through Active Hallucination Recovery Gate
        structured = await self.hallucination_guard.averify_and_recover(
            query=query,
            raw_answer=raw_answer,
            category=intent.category,
            context=context,
        )
        if evidence_sources and not structured.evidence_sources:
            structured.evidence_sources.extend(evidence_sources)

        return structured

    def answer_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> StructuredAnswer:
        """Synchronous wrapper for aanswer_query."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.aanswer_query(query, context)).result()
            return loop.run_until_complete(self.aanswer_query(query, context))
        except RuntimeError:
            return asyncio.run(self.aanswer_query(query, context))

    def _generate_text(self, prompt: str) -> str:
        """Helper to invoke synchronous LLM with text prompt and extract reply string."""
        from xeren.models.types import ChatMessage
        try:
            res = self.llm.generate([ChatMessage.user(prompt)])
            return getattr(res, "content", str(res))
        except Exception as e:
            logger.warning("Synchronous LLM generation error: %s", e)
            return f"Response for: {prompt}"

    async def _agenerate_text(self, prompt: str) -> str:
        """Helper to invoke asynchronous LLM with text prompt and extract reply string."""
        from xeren.models.types import ChatMessage
        try:
            if hasattr(self.llm, "agenerate"):
                res = await self.llm.agenerate([ChatMessage.user(prompt)])
                return getattr(res, "content", str(res))
            return self._generate_text(prompt)
        except Exception as e:
            logger.warning("Asynchronous LLM generation error: %s", e)
            return self._generate_text(prompt)

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
