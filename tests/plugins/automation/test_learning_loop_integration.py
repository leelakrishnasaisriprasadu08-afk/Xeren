"""End-to-end integration tests proving Automation Plugin participates in Xeren's learning loop.

Flows verified:
1. Failure path:
   Automation Task -> Step Failure -> Structured Outcome -> Verification ->
   Experience Plugin -> Failure Warning / Lesson -> Decision Context for Future Tasks.

2. Success path:
   Automation Task -> Execution Success -> Output Verification ->
   Experience Plugin -> Reusable Experience / Strategy Lesson -> Decision Context for Future Tasks.
"""

from xeren.core.runtime import XerenCore
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.automation.schemas import TaskStatus, TaskStep
from xeren.plugins.verification.schemas import (
    VerificationOperation,
    VerificationStatus,
)


def test_automation_failure_participates_in_experience_learning_loop():
    """
    Verify complete failure flow:
    1. Create an automation task.
    2. Execute the task.
    3. Make one step fail or produce an error.
    4. Automation records the structured failure/outcome.
    5. Verification evaluates the outcome.
    6. Experience Plugin records the relevant experience.
    7. A lesson or failure warning is produced.
    8. The experience can be retrieved for a similar future task.
    """
    core = XerenCore()
    auto_plugin = core.get_plugin("automation")
    assert isinstance(auto_plugin, AutomationPlugin)

    # Configure custom dispatcher: 'data' fails with a database connection timeout
    def failing_dispatcher(plugin: str, payload: dict, timeout=None):
        if plugin == "data":
            raise RuntimeError("DatabaseConnectionTimeout: Connection pool exhausted after 30s")
        return {"status": "ok"}

    auto_plugin.registry.set_custom_dispatcher(failing_dispatcher)

    # 1. Create automation task
    create_res = core.create_task(
        objective="Extract quarterly sales database metrics and generate executive report",
        steps=[
            TaskStep(id="fetch_sales", plugin_name="data", action="query"),
            TaskStep(
                id="generate_report",
                plugin_name="file",
                action="write",
                depends_on=["fetch_sales"],
            ),
        ],
    )
    assert create_res.success is True
    task_id = create_res.task_id
    assert task_id is not None

    # 2 & 3. Execute the task where fetch_sales fails
    exec_res = core.execute_task(task_id=task_id)

    # 4. Automation records structured failure outcome
    assert exec_res.success is False
    assert exec_res.status == TaskStatus.FAILED
    assert "fetch_sales" in exec_res.failed_steps
    assert "fetch_sales" in exec_res.step_errors
    assert "DatabaseConnectionTimeout" in exec_res.step_errors["fetch_sales"]
    assert len(exec_res.completed_steps) == 0

    outcome_payload = exec_res.to_experience_payload()
    assert outcome_payload["task_id"] == task_id
    assert outcome_payload["success"] is False
    assert outcome_payload["failed_steps"] == ["fetch_sales"]
    assert "DatabaseConnectionTimeout" in str(outcome_payload["errors"])

    # 5. Verification evaluates the outcome
    verif_res = core.verify(
        candidate=outcome_payload,
        operation=VerificationOperation.OUTPUT_VALIDATION,
        task="Extract quarterly sales database metrics and generate executive report",
    )
    assert verif_res is not None

    # 6. Experience Plugin records the relevant experience
    rec_res = core.record_automation_outcome(
        automation_result=exec_res,
        verification_status=verif_res.status.value,
        verification_score=verif_res.confidence_score,
        lesson="Database connection pools must be provisioned with health checks before batch extraction.",
        failure_avoidance_advice="Configure connection pooling with exponential retry backoff and keepalive ping.",
    )
    assert rec_res.success is True
    assert rec_res.item is not None
    assert rec_res.item.success is False
    assert "DatabaseConnectionTimeout" in str(rec_res.item.failure_reason)

    # 7. A lesson or failure warning is produced
    warnings = core.get_failure_warnings("Extract quarterly sales database metrics")
    assert len(warnings) >= 1
    assert any("DatabaseConnectionTimeout" in w.failure_reason for w in warnings)
    assert any("exponential retry" in w.avoidance_advice for w in warnings)

    # 8. The experience can be retrieved for a similar future task
    retrieved = core.retrieve_experiences(task="Extract quarterly sales metrics from database")
    assert len(retrieved) >= 1
    assert any(exp.selected_plugin == "automation" for exp in retrieved)

    context = core.get_decision_context("Extract sales database metrics")
    assert context is not None
    assert "PAST FAILURE WARNINGS" in context
    assert "DatabaseConnectionTimeout" in context
    assert "exponential retry" in context


def test_automation_success_participates_in_experience_learning_loop():
    """
    Verify complete success flow:
    1. Create an automation task.
    2. Execute the task successfully.
    3. Verification evaluates candidate outcome.
    4. Experience Plugin records it as reusable experience.
    5. Lessons/strategies are stored.
    6. Experience and lesson are available for a future similar task.
    """
    core = XerenCore()
    auto_plugin = core.get_plugin("automation")
    assert isinstance(auto_plugin, AutomationPlugin)

    # Configure custom dispatcher for successful multi-step pipeline
    def success_dispatcher(plugin: str, payload: dict, timeout=None):
        if plugin == "data":
            return {"profile": "Dataset contains 500 records with 0 missing values"}
        elif plugin == "research":
            return {"summary": "Executive summary: Churn risk reduced by 14% after feature update"}
        return {"status": "ok"}

    auto_plugin.registry.set_custom_dispatcher(success_dispatcher)

    # 1. Create automation task
    create_res = core.create_task(
        objective="Profile customer churn dataset and generate visual analytics summary",
        steps=[
            TaskStep(id="profile_data", plugin_name="data", action="profile"),
            TaskStep(
                id="generate_summary",
                plugin_name="research",
                action="synthesize",
                input_payload={"context": "${steps.profile_data.output.profile}"},
                depends_on=["profile_data"],
            ),
        ],
    )
    assert create_res.success is True
    task_id = create_res.task_id
    assert task_id is not None

    # 2. Execute task
    exec_res = core.execute_task(task_id=task_id)
    assert exec_res.success is True
    assert exec_res.status == TaskStatus.COMPLETED
    assert exec_res.completed_steps == ["profile_data", "generate_summary"]
    assert exec_res.failed_steps == []
    assert "generate_summary" in exec_res.step_results

    # 3. Verification evaluates candidate outcome
    summary_output = exec_res.step_results["generate_summary"]
    verif_res = core.verify(
        candidate=summary_output["summary"],
        operation=VerificationOperation.OUTPUT_VALIDATION,
        task="Profile customer churn dataset and generate visual analytics summary",
    )
    assert verif_res.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)

    # 4 & 5. Experience Plugin records verified reusable experience
    rec_res = core.record_automation_outcome(
        automation_result=exec_res,
        verification_status=verif_res.status.value,
        verification_score=verif_res.confidence_score,
        lesson="Multi-step dataset profiling followed by synthesis produces high-accuracy summaries.",
    )
    assert rec_res.success is True
    assert rec_res.item is not None
    assert rec_res.item.is_reusable is True
    assert rec_res.item.lesson == "Multi-step dataset profiling followed by synthesis produces high-accuracy summaries."

    # 6. Experience and lesson are available for future similar tasks
    retrieved = core.retrieve_experiences(task="Analyze customer churn dataset", success=True)
    assert len(retrieved) >= 1
    assert any(exp.selected_plugin == "automation" for exp in retrieved)

    context = core.get_decision_context("Analyze customer churn dataset and synthesize report")
    assert context is not None
    assert "SUCCESSFUL PREVIOUS STRATEGIES" in context
    assert "Multi-step dataset profiling followed by synthesis" in context
