"""Unit and integration tests for XerenCore interactive chat, task planning, and plan execution gating."""

import pytest

from xeren.core.data_holding import PermittedDataHoldingVault
from xeren.core.runtime import XerenCore
from xeren.core.session import XerenSession
from xeren.core.vault import UserVault
from xeren.models.providers.mock import MockLLM


@pytest.fixture
def test_core_env(tmp_path):
    vault_db = tmp_path / "core_vault.db"
    vault = UserVault(db_path=vault_db)
    session = XerenSession(vault=vault)
    data_holding = PermittedDataHoldingVault(vault=vault)
    llm = MockLLM()
    core = XerenCore(
        llm=llm,
        session=session,
        data_holding=data_holding,
    )
    return core, session, data_holding, vault, tmp_path


@pytest.mark.asyncio
async def test_general_chat_thought_discussion(test_core_env):
    core, session, _, _, _ = test_core_env

    # 1. Ask a general discussion query
    res = await core.achat("I have an idea about designing microservices for our AI agent, what do you think?")
    assert res["type"] == "chat_response"
    assert res["verified"] is True
    assert len(session.conversation_history) >= 2


@pytest.mark.asyncio
async def test_task_intent_stages_plan_first(test_core_env):
    core, session, _, _, _ = test_core_env

    # 1. Ask for a task: build a website
    task_query = "Build a modern landing page for my portfolio showcasing my AI projects"
    res = await core.achat(task_query)

    # 2. Verify plan was staged and NOT executed yet
    assert res["type"] == "plan_staged"
    assert "Execution Plan" in res["content"]
    assert "proceed to the plan" in res["content"]
    assert session.get_staged_plan() is not None
    assert session.staged_plan_status == "staged"


@pytest.mark.asyncio
async def test_proceed_to_plan_executes_staged_task(test_core_env):
    core, session, _, _, _ = test_core_env

    # 1. First stage a plan
    await core.achat("Create a landing page for my mobile app")
    assert session.get_staged_plan() is not None

    milestones_recorded = []

    async def _on_progress(progress):
        milestones_recorded.append(progress.get("phase"))

    # 2. Say "proceed to the plan"
    approval_res = await core.achat("proceed to the plan", on_progress=_on_progress)

    # 3. Verify execution completed
    assert approval_res["type"] == "plan_executed"
    assert approval_res["verified"] is True
    assert "Task Plan Executed Successfully" in approval_res["content"]

    # 4. Staged plan should now be cleared
    assert session.get_staged_plan() is None
    assert session.staged_plan_status == "idle"

    # 5. Milestones should have been emitted
    assert "understanding" in milestones_recorded
    assert "creating" in milestones_recorded
    assert "completed" in milestones_recorded


@pytest.mark.asyncio
async def test_data_holding_grounded_in_chat(test_core_env):
    core, _, data_holding, vault, tmp_path = test_core_env

    # 1. Grant directory and hold a secret project doc
    proj_dir = tmp_path / "permitted_dir"
    proj_dir.mkdir()
    secret_doc = proj_dir / "secret_specs.md"
    secret_doc.write_text("The secret project codename is Project Strawberry Velvet.", encoding="utf-8")

    vault.grant_directory(proj_dir, allow_write=True)
    data_holding.hold_device_file(secret_doc, secret_doc.read_text(encoding="utf-8"))

    # 2. Ask question related to the permitted document
    res = await core.achat("What is the secret project codename from our permitted specs?")
    assert res["type"] == "chat_response"
    assert res["verified"] is True


def test_is_plan_approval_patterns():
    assert XerenCore.is_plan_approval("proceed to the plan") is True
    assert XerenCore.is_plan_approval("proceed to plan") is True
    assert XerenCore.is_plan_approval("proceed") is True
    assert XerenCore.is_plan_approval("execute the plan") is True
    assert XerenCore.is_plan_approval("go ahead") is True
    assert XerenCore.is_plan_approval("what is the weather today?") is False
