"""Tests for Autonomous Agent integration with Workspace Intelligence: execution of workspace plan steps and safety."""

from pathlib import Path

from xeren.agent.actions import Action
from xeren.agent.controller import AgentController
from xeren.agent.executor import AgentExecutor
from xeren.agent.planner import MockPlanner, TaskPlan
from xeren.agent.validator import PlanValidator
from xeren.agent.state import TaskStatus
from xeren.plugins.manager import PluginManager
from xeren.workspace.manager import WorkspaceManager


def test_plan_validator_accepts_workspace_target():
    """Verify PlanValidator recognizes 'workspace' as a valid system target."""
    validator = PlanValidator()
    plan = TaskPlan(
        goal="Discover project files",
        steps=[
            Action(
                target="workspace",
                parameters={"operation": "discover", "goal": "Find auth code"},
                description="Discover authentication project files",
            )
        ],
    )
    res = validator.validate_plan(plan)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_agent_executor_executes_workspace_action(tmp_path: Path):
    """Verify AgentExecutor routes 'workspace' actions to WorkspaceManager."""
    ws_manager = WorkspaceManager()
    ws_manager.authorize_root(tmp_path, root_id="code_root")

    (tmp_path / "auth.py").write_text("def authenticate(): return True\n", encoding="utf-8")

    pm = PluginManager()
    executor = AgentExecutor(plugin_manager=pm, workspace_manager=ws_manager)

    action = Action(
        target="workspace",
        parameters={"operation": "discover", "goal": "Find auth implementation"},
        description="Discover auth files",
    )

    result = executor.execute(action)
    assert result.success is True
    assert result.output is not None
    assert "candidates" in result.output
    assert len(result.output["candidates"]) >= 1
    assert result.output["candidates"][0]["relative_path"] == "auth.py"


def test_agent_controller_autonomous_workspace_step_run(tmp_path: Path):
    """Verify AgentController executes a plan containing a workspace discovery step."""
    ws_manager = WorkspaceManager()
    ws_manager.authorize_root(tmp_path)

    (tmp_path / "dataset.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    plan = TaskPlan(
        goal="Analyze dataset",
        steps=[
            Action(
                target="workspace",
                parameters={"operation": "discover", "goal": "Find dataset"},
                description="Discover dataset",
            )
        ],
    )
    planner = MockPlanner(default_steps=plan.steps)

    controller = AgentController(
        planner=planner,
        workspace_manager=ws_manager,
    )

    state = controller.run("Analyze dataset")
    assert state.is_terminal is True
    assert state.status == TaskStatus.COMPLETED
    assert len(state.completed_steps) == 1
    step_res = state.completed_steps[0]
    assert step_res.success is True
    assert step_res.output is not None
