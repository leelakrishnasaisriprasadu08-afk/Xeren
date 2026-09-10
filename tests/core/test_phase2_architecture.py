"""Tests for Phase 2 Ultimate Xeren Architecture:
- 7-Stage Execution Lifecycle
- Epistemic Learner & Knowledge Gap Detector (Learn-First Engine)
- Windows Desktop Operator & Safe Shell Execution
- Universal Multi-Root Filesystem & Rollback Snapshots
- Browser Adapter integration in AgentExecutor
- End-to-End orchestration
"""

import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from xeren.agent.actions import Action, ActionResult, ActionType
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.executor import AgentExecutor
from xeren.core.intent import IntentClassifier, RoutingCategory
from xeren.core.learner import EpistemicLearner, KnowledgeGapDetector, KnowledgeGapEvaluation, LearnedKnowledge
from xeren.core.runtime import XerenCore
from xeren.models.providers.mock import MockLLM
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.automation.schemas import AutomationInput, AutomationOperation
from xeren.plugins.automation.tools.desktop import DesktopSecurityError, WindowsDesktopOperator
from xeren.plugins.file.plugin import FilePlugin
from xeren.plugins.file.schemas import FileInput, FileOperation
from xeren.plugins.file.tools.security import FileSecurityError, FileSecurityTool, PathTraversalError
from xeren.plugins.manager import PluginManager


class TestKnowledgeGapDetector(unittest.TestCase):
    """Test Stage 2 Knowledge Gap Detector."""

    def setUp(self):
        self.detector = KnowledgeGapDetector(confidence_threshold=0.75)

    def test_high_confidence_known_task(self):
        res = self.detector.evaluate("create a text file named hello.txt")
        self.assertFalse(res.has_gap)
        self.assertGreaterEqual(res.confidence_score, 0.75)

    def test_low_confidence_unknown_library(self):
        res = self.detector.evaluate("how do i use api foobar_quantum_sdk to authenticate?")
        self.assertTrue(res.has_gap)
        self.assertLess(res.confidence_score, 0.75)
        self.assertIsNotNone(res.gap_topic)

    def test_low_confidence_uncertainty_phrases(self):
        res = self.detector.evaluate("i don't know how to configure the new 2026 changelog settings")
        self.assertTrue(res.has_gap)
        self.assertTrue(any("Contains uncertainty indicator" in r for r in res.reasons))


class TestEpistemicLearner(unittest.IsolatedAsyncioTestCase):
    """Test Learn-First Engine execution."""

    async def test_alearn_topic_creates_plan_and_indexes(self):
        mock_llm = MockLLM()
        pm = PluginManager()
        # Mock knowledge and experience plugins
        mock_knowledge = MagicMock()
        mock_knowledge.name = "knowledge"
        mock_knowledge.version = "1.0.0"
        mock_knowledge.capabilities = ["knowledge_ingest"]
        mock_knowledge.initialize = MagicMock()
        mock_knowledge.aexecute = AsyncMock(return_value=MagicMock(success=True))

        mock_experience = MagicMock()
        mock_experience.name = "experience"
        mock_experience.version = "1.0.0"
        mock_experience.capabilities = ["experience_record"]
        mock_experience.initialize = MagicMock()
        mock_experience.aexecute = AsyncMock(return_value=MagicMock(success=True))

        pm.register(mock_knowledge)
        pm.register(mock_experience)

        learner = EpistemicLearner(llm=mock_llm, plugin_manager=pm)
        learned = await learner.alearn_topic("FastAPI lifespan handlers", depth="deep")

        self.assertIsInstance(learned, LearnedKnowledge)
        self.assertEqual(learned.topic, "FastAPI lifespan handlers")
        self.assertTrue(learned.indexed_in_rag)
        self.assertTrue(learned.indexed_in_experience)
        self.assertGreaterEqual(learned.confidence_score, 0.85)


class TestWindowsDesktopOperator(unittest.TestCase):
    """Test OS desktop app launching and supervised shell execution."""

    def setUp(self):
        self.operator = WindowsDesktopOperator()

    def test_resolve_known_app_names(self):
        # Notepad is guaranteed to exist on Windows
        resolved = self.operator.resolve_app_path("notepad")
        self.assertIsNotNone(resolved)
        self.assertTrue("notepad" in resolved.lower())

    def test_execute_safe_shell_command(self):
        res = self.operator.execute_shell("echo hello_xeren", timeout=5.0)
        self.assertTrue(res["success"])
        self.assertIn("hello_xeren", res["stdout"])

    def test_blocked_destructive_command(self):
        with self.assertRaises(DesktopSecurityError):
            self.operator.execute_shell("rmdir /s /q C:\\", timeout=5.0)


class TestMultiRootFilesystemAndSnapshots(unittest.TestCase):
    """Test Multi-Root Scoping and Pre-modification Snapshots."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_multi_root_user_home_allowed(self):
        user_home = Path.home()
        security = FileSecurityTool(workspace_dir=self.workspace, include_user_roots=True)
        # Ensure user home is an authorized root
        self.assertIn(user_home.resolve(), security.allowed_roots)

    def test_system_root_rejected(self):
        security = FileSecurityTool(workspace_dir=self.workspace, include_user_roots=True)
        with self.assertRaises(PathTraversalError):
            security.resolve_and_validate_path("C:\\Windows\\System32\\calc.exe")

    def test_file_workflow_creates_snapshot_on_overwrite(self):
        plugin = FilePlugin(workspace_dir=self.workspace)
        test_file = self.workspace / "sample.txt"
        test_file.write_text("initial version", encoding="utf-8")

        # Overwrite file
        res = plugin.workflow.execute_write(
            FileInput(
                operation=FileOperation.WRITE,
                path=str(test_file),
                content="updated version",
                overwrite=True,
            )
        )
        self.assertTrue(res.success)
        self.assertIn("snapshot", res.stats)
        snapshot_path = Path(res.stats["snapshot"])
        self.assertTrue(snapshot_path.exists())
        self.assertEqual(snapshot_path.read_text(encoding="utf-8"), "initial version")
        self.assertEqual(test_file.read_text(encoding="utf-8"), "updated version")


class TestAgentExecutorBrowserAdapter(unittest.IsolatedAsyncioTestCase):
    """Test direct browser adapter routing in AgentExecutor."""

    async def test_aexecute_browser_action(self):
        pm = PluginManager()
        browser = MockBrowserAdapter()
        executor = AgentExecutor(plugin_manager=pm, browser_adapter=browser)

        action = Action(
            action_id="browser_act_1",
            action_type=ActionType.BROWSER.value,
            target="browser",
            parameters={"operation": "navigate", "url": "https://example.com"},
        )
        res = await executor.aexecute(action)
        self.assertTrue(res.success)
        self.assertEqual(res.metadata.get("target"), "browser")


class TestEndToEnd7StageOrchestration(unittest.IsolatedAsyncioTestCase):
    """Test full 7-stage pipeline integration in XerenCore."""

    async def test_aanswer_query_with_learn_first_integration(self):
        core = XerenCore()
        # Query with uncertainty pattern triggering learn-first
        answer = await core.aanswer_query("teach me what is Python GIL in depth")
        self.assertIsNotNone(answer)
        self.assertTrue(len(answer.answer) > 0)
        self.assertGreaterEqual(answer.confidence_score, 0.70)


if __name__ == "__main__":
    unittest.main()
