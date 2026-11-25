"""Comprehensive 50+ Test Suite for Xeren Core & Plugins.

Validates the complete 7-Stage Active Automation and Epistemic Self-Learning system:
1. Intent + Task Analyzer (5 tests)
2. Knowledge Gap Detector & Learn-First Engine (5 tests)
3. Task Planner & Decomposition (5 tests)
4. Active File Plugin & Security (6 tests)
5. Windows Desktop & OS Operator (6 tests)
6. Active Coding Plugin & Sandbox (4 tests)
7. Active Browser & Strawberry Research (5 tests)
8. Knowledge & RAG Plugin (4 tests)
9. Verification Plugin & Claim Verifier (4 tests)
10. Experience Plugin & Pattern Detection (4 tests)
11. Observer, Evaluator & Self-Healing (4 tests)
12. End-to-End 7-Stage Orchestration (4 tests)

Total: 56 Test Cases
"""

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Core and Agent imports
from xeren.agent.actions import Action, ActionResult, ActionType, PermissionLevel
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.evaluator import DefaultCompletionEvaluator
from xeren.agent.executor import AgentExecutor
from xeren.agent.observer import DefaultObserver
from xeren.agent.recovery import DefaultRecoveryManager
from xeren.agent.state import TaskState
from xeren.agent.types import AgentState, AgentStatus
from xeren.core.hallucination_guard import HallucinationGuard, StructuredAnswer
from xeren.core.intent import IntentClassifier, IntentResult, RoutingCategory
from xeren.core.learner import EpistemicLearner, KnowledgeGapDetector, KnowledgeGapEvaluation, LearnedKnowledge
from xeren.core.planner import CorePlannerAdapter, PlanStep
from xeren.core.runtime import XerenCore
from xeren.models.providers.mock import MockLLM

# Plugin imports
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.automation.schemas import AutomationInput, AutomationOperation, StepStatus, TaskStep, TaskPlan
from xeren.plugins.automation.tools.desktop import DesktopSecurityError, WindowsDesktopOperator
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.schemas import CodingInput, CodingOperation
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.experience.schemas import ExperienceInput, ExperienceItem, ExperienceOperation
from xeren.plugins.experience.tools.patterns import ExperiencePatternTool
from xeren.plugins.file.plugin import FilePlugin
from xeren.plugins.file.schemas import FileInput, FileOperation
from xeren.plugins.file.tools.security import FileSecurityError, FileSecurityTool, PathTraversalError
from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.schemas import KnowledgeInput, KnowledgeOperation
from xeren.plugins.manager import PluginManager
from xeren.plugins.research.plugin import ResearchPlugin
from xeren.plugins.research.tools.claim_verifier import ClaimStatus, ClaimVerifier
from xeren.plugins.research.tools.credibility_scorer import CredibilityScorer
from xeren.plugins.research.tools.strawberry_planner import StrawberryPlan, StrawberryQueryPlanner
from xeren.plugins.verification.plugin import VerificationPlugin
from xeren.plugins.verification.schemas import VerificationInput, VerificationOperation


# =============================================================================
# 1. Intent + Task Analyzer (5 tests)
# =============================================================================
class TestStage1IntentAnalyzer(unittest.TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()

    def test_01_route_action_request(self):
        res = self.classifier.classify("open chrome and download the release file")
        self.assertEqual(res.category, RoutingCategory.ACTION_REQUEST)
        self.assertGreaterEqual(res.confidence, 0.70)

    def test_02_route_project_query(self):
        res = self.classifier.classify("how does the xeren rag architecture work?")
        self.assertEqual(res.category, RoutingCategory.XEREN_PROJECT)
        self.assertGreaterEqual(res.confidence, 0.70)

    def test_03_route_general_knowledge(self):
        res = self.classifier.classify("what is the speed of light in vacuum?")
        self.assertEqual(res.category, RoutingCategory.GENERAL_KNOWLEDGE)
        self.assertGreaterEqual(res.confidence, 0.70)

    def test_04_complex_multiclause_intent(self):
        res = self.classifier.classify("please search the web for latest python features and write them to a file")
        self.assertEqual(res.category, RoutingCategory.ACTION_REQUEST)

    def test_05_context_override_category(self):
        res = self.classifier.classify("simple text", context={"force_category": "xeren_project"})
        self.assertEqual(res.category, RoutingCategory.XEREN_PROJECT)


# =============================================================================
# 2. Knowledge Gap Detector & Learn-First Engine (5 tests)
# =============================================================================
class TestStage2KnowledgeGapAndLearnFirst(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.detector = KnowledgeGapDetector(confidence_threshold=0.75)
        self.llm = MockLLM()
        self.pm = PluginManager()
        self.learner = EpistemicLearner(llm=self.llm, plugin_manager=self.pm)

    def test_06_high_confidence_bypasses_gap(self):
        eval_res = self.detector.evaluate("write a hello world script in python")
        self.assertFalse(eval_res.has_gap)
        self.assertGreaterEqual(eval_res.confidence_score, 0.75)

    def test_07_unknown_library_triggers_gap(self):
        eval_res = self.detector.evaluate("how to use lib hyper_quant_v3 for distributed training")
        self.assertTrue(eval_res.has_gap)
        self.assertLess(eval_res.confidence_score, 0.75)
        self.assertIsNotNone(eval_res.gap_topic)

    def test_08_uncertainty_phrases_lower_confidence(self):
        eval_res = self.detector.evaluate("i don't know the parameters for 2026 sdk release notes")
        self.assertTrue(eval_res.has_gap)
        self.assertTrue(any("uncertainty indicator" in r for r in eval_res.reasons))

    async def test_09_learn_first_synthesizes_knowledge(self):
        learned = await self.learner.alearn_topic("asyncio task groups", depth="deep")
        self.assertIsInstance(learned, LearnedKnowledge)
        self.assertEqual(learned.topic, "asyncio task groups")
        self.assertTrue(len(learned.summary) > 0)
        self.assertGreaterEqual(learned.confidence_score, 0.80)

    async def test_10_learn_first_indexes_into_plugins(self):
        mock_k = MagicMock(name="knowledge")
        mock_k.name = "knowledge"
        mock_k.version = "1.0.0"
        mock_k.capabilities = ["knowledge_ingest"]
        mock_k.initialize = MagicMock()
        mock_k.aexecute = AsyncMock(return_value=MagicMock(success=True))

        mock_e = MagicMock(name="experience")
        mock_e.name = "experience"
        mock_e.version = "1.0.0"
        mock_e.capabilities = ["experience_record"]
        mock_e.initialize = MagicMock()
        mock_e.aexecute = AsyncMock(return_value=MagicMock(success=True))

        self.pm.register(mock_k)
        self.pm.register(mock_e)

        learned = await self.learner.alearn_topic("Pydantic v2 model_validator", depth="deep")
        self.assertTrue(learned.indexed_in_rag)
        self.assertTrue(learned.indexed_in_experience)


# =============================================================================
# 3. Task Planner & Decomposition (5 tests)
# =============================================================================
class TestStage3TaskPlanner(unittest.TestCase):
    def test_11_plan_creation_with_steps(self):
        steps = [
            TaskStep(id="s1", plugin_name="file", operation="read", title="Read config"),
            TaskStep(id="s2", plugin_name="coding", operation="execute", depends_on=["s1"], title="Run code"),
        ]
        plan = TaskPlan(objective="Process data", steps=steps)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[1].depends_on, ["s1"])

    def test_12_plan_acyclic_dependencies(self):
        s1 = TaskStep(id="step_a", plugin_name="research", operation="search")
        s2 = TaskStep(id="step_b", plugin_name="file", operation="write", depends_on=["step_a"])
        plan = TaskPlan(objective="Search and write", steps=[s1, s2])
        self.assertIn("step_a", plan.steps[1].depends_on)

    def test_13_plan_step_normalization(self):
        raw_step = {"plugin_name": "automation", "action": "desktop_launch", "input_data": {"app_name": "notepad"}}
        step = TaskStep.model_validate(raw_step)
        self.assertEqual(step.plugin_name, "automation")
        self.assertEqual(step.operation, "desktop_launch")
        self.assertIsNotNone(step.id)

    def test_14_plan_step_retry_policy(self):
        step = TaskStep(plugin_name="api", operation="request")
        self.assertEqual(step.retry_policy.max_retries, 2)
        self.assertGreaterEqual(step.retry_policy.backoff_factor, 1.0)

    def test_15_plan_timeout_defaults(self):
        plan = TaskPlan(objective="Test plan")
        self.assertEqual(plan.timeout_seconds, 300.0)


# =============================================================================
# 4. Active File Plugin & Security (6 tests)
# =============================================================================
class TestStage4ActiveFilePlugin(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.plugin = FilePlugin(workspace_dir=self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_16_file_write_and_read(self):
        fpath = self.workspace / "test.txt"
        w_res = self.plugin.workflow.execute_write(
            FileInput(operation=FileOperation.WRITE, path=str(fpath), content="hello xeren")
        )
        self.assertTrue(w_res.success)

        r_res = self.plugin.workflow.execute_read(
            FileInput(operation=FileOperation.READ, path=str(fpath))
        )
        self.assertTrue(r_res.success)
        self.assertEqual(r_res.content, "hello xeren")

    def test_17_multi_root_user_home_allowed(self):
        user_home = Path.home().resolve()
        security = FileSecurityTool(workspace_dir=self.workspace, include_user_roots=True)
        self.assertIn(user_home, security.allowed_roots)

    def test_18_system_root_prefix_blocked(self):
        security = FileSecurityTool(workspace_dir=self.workspace)
        with self.assertRaises(PathTraversalError):
            security.resolve_and_validate_path("C:\\Windows\\System32\\cmd.exe")

    def test_19_automatic_rollback_snapshot_on_overwrite(self):
        fpath = self.workspace / "doc.md"
        fpath.write_text("v1 content", encoding="utf-8")

        res = self.plugin.workflow.execute_write(
            FileInput(operation=FileOperation.WRITE, path=str(fpath), content="v2 content", overwrite=True)
        )
        self.assertTrue(res.success)
        self.assertIn("snapshot", res.stats)
        snap = Path(res.stats["snapshot"])
        self.assertTrue(snap.exists())
        self.assertEqual(snap.read_text(encoding="utf-8"), "v1 content")

    def test_20_null_byte_in_path_blocked(self):
        security = FileSecurityTool(workspace_dir=self.workspace)
        with self.assertRaises(FileSecurityError):
            security.resolve_and_validate_path("malicious\0file.txt")

    def test_21_reserved_device_name_blocked(self):
        security = FileSecurityTool(workspace_dir=self.workspace)
        with self.assertRaises(FileSecurityError):
            security.resolve_and_validate_path("CON.txt")


# =============================================================================
# 5. Windows Desktop & OS Operator (6 tests)
# =============================================================================
class TestStage4WindowsDesktopOperator(unittest.TestCase):
    def setUp(self):
        self.operator = WindowsDesktopOperator()
        self.plugin = AutomationPlugin()

    def test_22_resolve_known_app_notepad(self):
        resolved = self.operator.resolve_app_path("notepad")
        self.assertIsNotNone(resolved)
        self.assertIn("notepad", resolved.lower())

    def test_23_resolve_known_app_calc(self):
        resolved = self.operator.resolve_app_path("calc")
        self.assertIsNotNone(resolved)
        self.assertTrue(resolved.lower().endswith(".exe") or "calc" in resolved.lower())

    def test_24_execute_safe_powershell_command(self):
        res = self.operator.execute_shell("echo 'xeren_active'", timeout=5.0)
        self.assertTrue(res["success"])
        self.assertIn("xeren_active", res["stdout"])

    def test_25_blocked_destructive_system_command(self):
        with self.assertRaises(DesktopSecurityError):
            self.operator.execute_shell("rmdir /s /q C:\\", timeout=5.0)

    def test_26_command_timeout_protection(self):
        res = self.operator.execute_shell("Start-Sleep -Seconds 4", timeout=0.5)
        self.assertFalse(res["success"])
        self.assertIn("timed out", res["stderr"].lower())

    def test_27_desktop_operation_via_automation_plugin(self):
        inp = AutomationInput(
            operation=AutomationOperation.DESKTOP_COMMAND,
            command="echo 'plugin_bridge_ok'",
        )
        res = self.plugin.workflow.run(inp)
        self.assertTrue(res.success)
        self.assertIn("plugin_bridge_ok", res.metadata.get("stdout", ""))


# =============================================================================
# 6. Active Coding Plugin & Sandbox (4 tests)
# =============================================================================
class TestStage4ActiveCodingPlugin(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.plugin = CodingPlugin()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_28_coding_manifest_capabilities(self):
        caps = self.plugin.manifest.capabilities
        self.assertIn("code_generation", caps)
        self.assertIn("code_execution", caps)

    def test_29_coding_input_validation(self):
        inp = CodingInput(
            operation=CodingOperation.GENERATE,
            task="def add(a, b): return a + b",
            language="python",
        )
        self.assertEqual(inp.language, "python")
        self.assertEqual(inp.operation, CodingOperation.GENERATE)

    def test_30_coding_execution_sandbox_init(self):
        executor = self.plugin.registry.executor
        self.assertIsNotNone(executor)

    def test_31_coding_ast_analysis_tool(self):
        analyzer = self.plugin.registry.analysis_tool
        self.assertIsNotNone(analyzer)


# =============================================================================
# 7. Active Browser & Strawberry Research (5 tests)
# =============================================================================
class TestStage4ActiveBrowserAndResearch(unittest.IsolatedAsyncioTestCase):
    def test_32_strawberry_4_angle_plan(self):
        planner = StrawberryQueryPlanner()
        plan = planner.create_plan("Quantum Computing algorithms", depth="deep")
        self.assertIsInstance(plan, StrawberryPlan)
        angle_types = [a.angle_type for a in plan.angles]
        self.assertIn("factual", angle_types)
        self.assertIn("counterfactual", angle_types)
        self.assertIn("statistical", angle_types)
        self.assertIn("consensus", angle_types)

    def test_33_strawberry_sanitizes_pii_before_search(self):
        planner = StrawberryQueryPlanner()
        plan = planner.create_plan("My api_key is sk-1234567890123456789012345 for API", depth="fast")
        for angle in plan.angles:
            self.assertNotIn("sk-1234567890123456789012345", angle.query)

    def test_34_mock_browser_navigation(self):
        browser = MockBrowserAdapter()
        obs = browser.navigate("https://example.com")
        self.assertEqual(obs.url, "https://example.com")
        self.assertEqual(obs.status_code, 200)

    def test_35_mock_browser_type_and_click(self):
        browser = MockBrowserAdapter()
        browser.type("input#search", "xeren AI")
        browser.click("button#submit")
        self.assertEqual(len(browser.typed_inputs), 1)
        self.assertEqual(browser.typed_inputs[0]["text"], "xeren AI")
        self.assertIn("button#submit", browser.clicked_selectors)

    async def test_36_agent_executor_routes_browser_action(self):
        pm = PluginManager()
        browser = MockBrowserAdapter()
        executor = AgentExecutor(plugin_manager=pm, browser_adapter=browser)
        action = Action(
            action_id="act_nav",
            target="browser",
            parameters={"operation": "navigate", "url": "https://example.com"},
        )
        res = await executor.aexecute(action)
        self.assertTrue(res.success)
        self.assertEqual(browser.current_url, "https://example.com")


# =============================================================================
# 8. Knowledge & RAG Plugin (4 tests)
# =============================================================================
class TestKnowledgeAndRAGPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = KnowledgePlugin()

    def test_37_knowledge_input_requires_query_on_search(self):
        with self.assertRaises(ValueError):
            KnowledgeInput(operation=KnowledgeOperation.QUERY, query="")

    def test_38_knowledge_ingest_requires_texts_or_docs(self):
        with self.assertRaises(ValueError):
            KnowledgeInput(operation=KnowledgeOperation.INGEST)

    def test_39_knowledge_valid_ingest_input(self):
        inp = KnowledgeInput(
            operation=KnowledgeOperation.INGEST,
            texts=["Xeren Core is a 7-stage autonomous AI system."],
            metadata={"source": "unit_test"},
        )
        self.assertEqual(len(inp.texts), 1)

    def test_40_knowledge_retrieval_mode_options(self):
        inp = KnowledgeInput(operation=KnowledgeOperation.QUERY, query="xeren architecture", top_k=3)
        self.assertEqual(inp.top_k, 3)
        self.assertEqual(inp.retrieval_mode.value, "hybrid")


# =============================================================================
# 9. Verification Plugin & Claim Verifier (4 tests)
# =============================================================================
class TestVerificationPluginAndClaims(unittest.TestCase):
    def setUp(self):
        self.claim_verifier = ClaimVerifier()
        self.scorer = CredibilityScorer()
        self.plugin = VerificationPlugin()

    def test_41_claim_verifier_supported(self):
        evidence = [
            {"url": "https://python.org", "excerpt": "Python was created by Guido van Rossum", "supports": True},
            {"url": "https://docs.python.org", "excerpt": "Guido van Rossum developed Python", "supports": True},
        ]
        result = self.claim_verifier.verify_claim("Python was created by Guido van Rossum", evidence)
        self.assertEqual(result.status, ClaimStatus.VERIFIED)
        self.assertGreaterEqual(result.confidence, 0.70)

    def test_42_claim_verifier_unsupported(self):
        evidence = [{"url": "https://python.org", "excerpt": "The sky is blue", "supports": False}]
        result = self.claim_verifier.verify_claim("Python runs natively on Mars rovers without an interpreter", evidence)
        self.assertEqual(result.status, ClaimStatus.UNVERIFIED)

    def test_43_credibility_score_authority_domain(self):
        report = self.scorer.evaluate_url("https://docs.python.org/3/whatsnew/index.html")
        self.assertGreaterEqual(report.credibility_score, 0.80)

    def test_44_verification_plugin_execution(self):
        inp = VerificationInput(
            operation=VerificationOperation.OUTPUT_VALIDATION,
            candidate="File test.txt created successfully",
            task="Create file test.txt",
        )
        res = self.plugin.execute(inp)
        self.assertTrue(res.success)


# =============================================================================
# 10. Experience Plugin & Pattern Detection (4 tests)
# =============================================================================
class TestExperiencePluginAndPatterns(unittest.TestCase):
    def setUp(self):
        self.pattern_tool = ExperiencePatternTool()
        self.plugin = ExperiencePlugin()

    def test_45_pattern_detection_high_reliability(self):
        experiences = [
            ExperienceItem(task="read file", selected_plugin="file", action="read", success=True, confidence=0.95),
            ExperienceItem(task="read file", selected_plugin="file", action="read", success=True, confidence=0.90),
        ]
        patterns = self.pattern_tool.detect_patterns(experiences)
        self.assertTrue(any(p.get("pattern_type") == "high_reliability" for p in patterns))

    def test_46_pattern_detection_failure_risk(self):
        experiences = [
            ExperienceItem(task="delete root", selected_plugin="file", action="delete", success=False, failure_reason="Forbidden"),
            ExperienceItem(task="delete root", selected_plugin="file", action="delete", success=False, failure_reason="Forbidden"),
        ]
        patterns = self.pattern_tool.detect_patterns(experiences)
        self.assertTrue(any(p.get("pattern_type") == "high_failure_risk" for p in patterns))

    def test_47_lesson_extraction_from_failures(self):
        experiences = [
            ExperienceItem(
                task="network request",
                selected_plugin="api",
                action="request",
                success=False,
                failure_avoidance_advice="Ensure API key is set before requesting",
            )
        ]
        lessons = self.pattern_tool.extract_lessons(experiences)
        self.assertEqual(len(lessons), 1)
        self.assertIn("Ensure API key is set", lessons[0].lesson)

    def test_48_experience_plugin_record_execution(self):
        inp = ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Execute command",
            plugin_name="automation",
            action="desktop_command",
            success=True,
        )
        res = self.plugin.execute(inp)
        self.assertTrue(res.success)


# =============================================================================
# 11. Observer, Evaluator & Self-Healing (4 tests)
# =============================================================================
class TestObserverEvaluatorAndSelfHealing(unittest.TestCase):
    def setUp(self):
        self.observer = DefaultObserver()
        self.evaluator = DefaultCompletionEvaluator()
        self.recovery = DefaultRecoveryManager(max_total_cycles=5)

    def test_49_observer_captures_action_result(self):
        action = Action(target="file", parameters={"path": "test.txt"})
        result = ActionResult(action_id=action.action_id, success=True, output={"bytes": 128})
        state = AgentState(task="test")
        obs = self.observer.observe(action, result, state)
        self.assertIsNotNone(obs)

    def test_50_evaluator_evaluates_completed_state(self):
        state = TaskState(
            goal="sample task",
            completed_steps=[ActionResult(action_id="act_1", success=True, output="ok")],
        )
        eval_res = self.evaluator.evaluate(state)
        self.assertIsNotNone(eval_res)
        self.assertTrue(eval_res.is_complete)

    def test_51_recovery_manager_records_attempt_and_retries(self):
        action = Action(target="network", parameters={"url": "http://err"})
        result = ActionResult(action_id=action.action_id, success=False, error="Connection reset")
        state = AgentState(task="network fetch")
        strat = self.recovery.handle_failure(action, result, state)
        self.assertIn(strat, ["retry", "replan", "fail", "wait_approval"])

    def test_52_recovery_manager_exceeds_max_cycles(self):
        recovery = DefaultRecoveryManager(max_total_cycles=1)
        action = Action(target="test", parameters={})
        res = ActionResult(action_id=action.action_id, success=False, error="fatal")
        state = AgentState(task="test", step_count=1)
        strat = recovery.handle_failure(action, res, state)
        self.assertEqual(strat, "fail")


# =============================================================================
# 12. End-to-End 7-Stage Orchestration (4 tests)
# =============================================================================
class TestEndToEnd7StageOrchestration(unittest.IsolatedAsyncioTestCase):
    async def test_53_general_query_with_hallucination_guard(self):
        core = XerenCore()
        ans: StructuredAnswer = await core.aanswer_query("Explain gravity in physics")
        self.assertIsInstance(ans, StructuredAnswer)
        self.assertTrue(len(ans.answer) > 0)
        self.assertGreaterEqual(ans.confidence_score, 0.70)

    async def test_54_unknown_topic_triggers_stage2_learn_first(self):
        core = XerenCore()
        ans: StructuredAnswer = await core.aanswer_query("teach me how to configure unreleased 2026 quantum sdk api")
        self.assertIsInstance(ans, StructuredAnswer)
        self.assertGreaterEqual(ans.confidence_score, 0.70)

    async def test_55_action_request_desktop_command_pipeline(self):
        core = XerenCore()
        ans: StructuredAnswer = await core.aanswer_query("run powershell command echo 'xeren_7_stages_verified'")
        self.assertIsInstance(ans, StructuredAnswer)
        self.assertTrue(len(ans.answer) > 0)

    async def test_56_synchronous_wrapper_answers_query(self):
        core = XerenCore()
        ans: StructuredAnswer = core.answer_query("What is the capital of France?")
        self.assertIsInstance(ans, StructuredAnswer)
        self.assertGreaterEqual(ans.confidence_score, 0.70)


if __name__ == "__main__":
    unittest.main()
