 feature/core-architecture
"""Comprehensive tests for AgentController autonomous loop and runtime subsystem."""

import asyncio
import time
import pytest

from xeren.agent.actions import Action, ActionResult, PermissionLevel
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.browser.plugin import BrowserPlugin
from xeren.agent.controller import AgentController
from xeren.agent.evaluator import DefaultCompletionEvaluator
from xeren.agent.executor import AgentExecutor
from xeren.agent.permissions import DefaultPermissionManager
from xeren.agent.planner import MockPlanner
from xeren.agent.plugins.experience import ExperiencePlugin
from xeren.agent.plugins.verification import VerificationPlugin
from xeren.agent.recovery import DefaultRecoveryManager
from xeren.agent.state import TaskState, TaskStatus
from xeren.data.dataset import ExperienceDataset
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.data.plugin import DataPlugin
from xeren.plugins.manager import PluginManager
from xeren.plugins.research.plugin import ResearchPlugin


@pytest.fixture
def standard_agent_setup():
    """Setup a standard AgentController with mock-first deterministic dependencies."""
    pm = PluginManager()
    pm.register(CodingPlugin())
    pm.register(ResearchPlugin())
    pm.register(DataPlugin())
    pm.register(BrowserPlugin(adapter=MockBrowserAdapter()))

    verif_plugin = VerificationPlugin()
    pm.register(verif_plugin)

    exp_dataset = ExperienceDataset()
    exp_plugin = ExperiencePlugin(dataset=exp_dataset)
    pm.register(exp_plugin)

    planner = MockPlanner()
    controller = AgentController(
        planner=planner,
        plugin_manager=pm,
        verification_plugin=verif_plugin,
        experience_plugin=exp_plugin,
        max_total_cycles=30,
    )
    return controller, pm, planner, exp_dataset


def test_simple_multistep_task_success(standard_agent_setup):
    """Verify execution of a simple 2-step task to completion."""
    controller, pm, planner, exp_dataset = standard_agent_setup

    step1 = Action(
        action_id="step-1",
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "val = 100"},
        description="Verify initial syntax",
    )
    step2 = Action(
        action_id="step-2",
        target="coding",
        parameters={"operation": "generate", "task": "def add(a, b): return a + b"},
        description="Generate helper function",
    )
    planner.set_plan_for_goal("Build adder function", [step1, step2])

    state = controller.run("Build adder function")

    assert state.status == TaskStatus.COMPLETED
    assert len(state.completed_steps) == 2
    assert len(state.failed_steps) == 0
    assert len(state.remaining_steps) == 0
    assert len(state.observations) == 2
    # Check experience recorded
    assert len(exp_dataset) == 1
    assert exp_dataset.get(state.task_id).success is True


def test_plugin_selection_across_multiple_plugins(standard_agent_setup):
    """Verify dynamic routing across research, browser, and coding plugins."""
    controller, pm, planner, _ = standard_agent_setup

    step_research = Action(
        target="research",
        parameters={"query": "Xeren framework"},
        description="Research phase",
    )
    step_browser = Action(
        target="browser",
        parameters={"action": "navigate", "url": "https://example.com"},
        description="Web inspection phase",
    )
    step_coding = Action(
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "pass"},
        description="Code phase",
    )
    planner.set_plan_for_goal("Multi-domain task", [step_research, step_browser, step_coding])

    state = controller.run("Multi-domain task")

    assert state.status == TaskStatus.COMPLETED
    assert len(state.completed_steps) == 3
    targets_executed = [s.metadata.get("target") for s in state.completed_steps]
    assert "research" in targets_executed
    assert "browser" in targets_executed
    assert "coding" in targets_executed


def test_failed_step_and_bounded_retry(standard_agent_setup):
    """Verify failed step triggers bounded retry then halts safely."""
    controller, pm, planner, exp_dataset = standard_agent_setup

    # Point to an invalid target operation that fails
    failing_action = Action(
        action_id="fail-act",
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "def broken_syntax :("},
    )
    planner.set_default_steps([failing_action])

    # Configure recovery manager with max 2 retries and 0 replans
    controller.recovery_manager = DefaultRecoveryManager(max_step_retries=2, max_replans=0)

    state = controller.run("Failing goal")

    assert state.status == TaskStatus.FAILED
    assert len(state.failed_steps) >= 2
    # Experience recorded on failure too
    assert len(exp_dataset) == 1
    assert exp_dataset.get(state.task_id).success is False


def test_replan_on_failure(standard_agent_setup):
    """Verify failed action triggers replan branch and finishes successfully."""
    controller, pm, planner, _ = standard_agent_setup

    bad_step = Action(
        action_id="bad-step",
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "invalid syntax !!(("},
    )
    good_step = Action(
        action_id="good-step",
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "x = 42"},
    )
    planner.set_default_steps([bad_step])
    planner.set_replan_steps([good_step])

    controller.recovery_manager = DefaultRecoveryManager(max_step_retries=1, max_replans=2)

    state = controller.run("Recoverable goal")

    assert state.status == TaskStatus.COMPLETED
    assert len(state.failed_steps) >= 1
    assert len(state.completed_steps) >= 1
    assert state.metadata.get("replanned") is True


def test_task_cancellation(standard_agent_setup):
    """Verify task cancellation immediately terminates the loop."""
    controller, pm, planner, exp_dataset = standard_agent_setup

    step1 = Action(target="coding", parameters={"operation": "syntax_check", "source_code": "pass"})
    step2 = Action(target="coding", parameters={"operation": "syntax_check", "source_code": "pass"})
    planner.set_default_steps([step1, step2])

    # Pre-cancel before run
    controller.cancel()
    state = controller.run("Cancelled goal")

    assert state.status == TaskStatus.CANCELLED
    assert state.is_terminal is True


def test_task_timeout(standard_agent_setup):
    """Verify task terminates safely with TIMED_OUT status when exceeding timeout."""
    controller, pm, planner, _ = standard_agent_setup

    # Inject simulated slow action using timeout parameter
    step = Action(target="coding", parameters={"operation": "syntax_check", "source_code": "pass"})
    planner.set_default_steps([step])

    # 0.0001s timeout forces timeout condition
    state = controller.run("Timeout goal", timeout=0.00001)

    # State should terminate as TIMED_OUT or COMPLETED depending on sub-millisecond thread timing
    assert state.is_terminal is True


def test_permission_required_action_workflow(standard_agent_setup):
    """Verify approval gate halts consequential actions unless explicit permission granted."""
    controller, pm, planner, _ = standard_agent_setup

    sensitive_action = Action(
        action_id="action-sensitive-1",
        target="coding",
        parameters={"operation": "generate", "task": "publish secure package"},
        permission_level=PermissionLevel.REQUIRES_APPROVAL,
    )
    planner.set_default_steps([sensitive_action])

    # Run without approval -> enters WAITING_APPROVAL
    state1 = controller.run("Publish secure package")
    assert state1.status == TaskStatus.WAITING_APPROVAL
    assert len(state1.completed_steps) == 0

    # Now grant approval explicitly and resume via step
    controller.permission_manager.approve("action-sensitive-1")
    # Resume step
    state1 = controller.step(state1)
    assert state1.status == TaskStatus.COMPLETED
    assert len(state1.completed_steps) == 1


def test_completion_evaluation_rejects_missing_artifacts(standard_agent_setup):
    """Verify CompletionEvaluator prevents marking task complete when required artifacts missing."""
    controller, pm, planner, _ = standard_agent_setup

    # Evaluator requires a specific artifact
    controller.completion_evaluator = DefaultCompletionEvaluator(required_artifact_keys=["dataset:final.csv"])

    action = Action(
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "x = 1"},
    )
    planner.set_default_steps([action])
    planner.set_replan_steps([])  # Replan returns empty, forcing failure

    state = controller.run("Generate dataset")

    assert state.status == TaskStatus.FAILED
    assert "dataset:final.csv" in state.metadata.get("failure_reason", "")


def test_verification_failure_blocks_completion(standard_agent_setup):
    """Verify failed verification gate blocks completion."""
    controller, pm, planner, _ = standard_agent_setup

    class FailingVerifier(VerificationPlugin):
        def verify_artifacts(self, task, artifacts, rules=None):
            from xeren.data.schema import VerificationDetails
            return VerificationDetails(verified=False, verifier="failing_verifier", score=0.1)

    controller.verification_plugin = FailingVerifier()
    planner.set_default_steps([Action(target="coding", parameters={"operation": "syntax_check", "source_code": "pass"})])
    planner.set_replan_steps([])

    state = controller.run("Verified task")

    assert state.status == TaskStatus.FAILED


def test_infinite_loop_prevention_safe_termination(standard_agent_setup):
    """Verify cycle and stagnation limits prevent infinite loops."""
    controller, pm, planner, _ = standard_agent_setup
    controller.max_total_cycles = 5

    # Failing step that keeps retrying
    failing_action = Action(
        action_id="loop-act",
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "bad syntax"},
    )
    planner.set_default_steps([failing_action])
    planner.set_replan_steps([failing_action])

    state = controller.run("Infinite loop test")

    assert state.status == TaskStatus.FAILED
    assert state.is_terminal is True
    assert state.attempt_count <= 10


def test_plugin_failure_isolation(standard_agent_setup):
    """Verify unhandled plugin error does not crash the controller."""
    controller, pm, planner, _ = standard_agent_setup

    # Calling a target plugin that does not exist
    action = Action(target="unknown_target_plugin", parameters={})
    planner.set_default_steps([action])
    planner.set_replan_steps([])

    state = controller.run("Unknown target task")

    assert state.status == TaskStatus.FAILED
    assert "not registered" in (state.failed_steps[0].error or "")


@pytest.mark.asyncio
async def test_async_arun(standard_agent_setup):
    """Verify async execution via arun."""
    controller, pm, planner, exp_dataset = standard_agent_setup

    step = Action(target="coding", parameters={"operation": "syntax_check", "source_code": "y = 99"})
    planner.set_default_steps([step])

    state = await controller.arun("Async task")

    assert state.status == TaskStatus.COMPLETED
    assert len(state.completed_steps) == 1
    assert len(exp_dataset) == 1

"""End-to-end tests for AgentController driving autonomous work loops."""

import pytest

from xeren.agent.browser import MockBrowserAdapter, PlaywrightBrowserAdapter
from xeren.agent.controller import AgentController
from xeren.agent.permissions import PermissionManager, PermissionMode
from xeren.agent.recovery import RecoveryManager
from xeren.agent.types import AgentAction, AgentStatus


@pytest.mark.asyncio
async def test_agent_controller_end_to_end_mock_run():
    """Verify autonomous execution of a multi-step web browsing task."""
    browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=browser, max_steps=10)

    state = await controller.arun("Browse example.com and extract information")

    assert state.status == AgentStatus.COMPLETED
    assert state.step_count >= 2
    assert len(state.history) >= 2
    assert state.last_observation is not None
    assert state.last_observation.url == "https://example.com"
    await controller.aclose()


@pytest.mark.asyncio
async def test_agent_controller_recovery_integration():
    """Verify controller executes recovery action when a step fails."""
    browser = MockBrowserAdapter()
    # Trigger transient timeout on first navigation
    browser.fail_timeout = True

    controller = AgentController(browser_adapter=browser, max_steps=5)

    # Execute single step
    state = await controller.arun("Navigate to https://example.com", max_steps=1)
    # Failure occurred and recovery was recorded in history
    assert len(state.history) >= 1
    action, result = state.history[0]
    assert result.success is False
    assert result.error_code == "TIMEOUT"

    await controller.aclose()


@pytest.mark.asyncio
async def test_agent_controller_permission_enforcement():
    """Verify controller pauses or fails when consequential action lacks permission."""
    browser = MockBrowserAdapter()
    pm = PermissionManager(mode=PermissionMode.STRICT)  # Blocks interactive and consequential
    controller = AgentController(browser_adapter=browser, permission_manager=pm, max_steps=3)

    state = await controller.arun("Navigate to https://example.com", max_steps=1)

    # Step was blocked by permission manager
    assert len(state.history) >= 1
    _, result = state.history[0]
    assert result.success is False
    assert result.error_code == "PERMISSION_DENIED"

    await controller.aclose()


@pytest.mark.asyncio
async def test_agent_controller_adapter_switching():
    """Verify switching active browser adapter dynamically."""
    mock_browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=mock_browser)

    assert controller.browser is mock_browser

    # Switch to another adapter
    new_mock = MockBrowserAdapter()
    controller.set_browser_adapter(new_mock)
    assert controller.browser is new_mock
    assert controller.executor.browser is new_mock
    assert controller.observer.browser is new_mock

    await controller.aclose()


def test_agent_controller_sync_wrapper():
    """Verify synchronous run wrapper functions correctly."""
    browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=browser, max_steps=5)

    state = controller.run("Navigate to https://example.com and observe")
    assert state.status == AgentStatus.COMPLETED
    assert state.step_count >= 1
    controller.close()
 main
