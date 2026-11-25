"""Thread-safe state management and history logging for Automation Plugin tasks."""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional

from xeren.plugins.automation.schemas import (
    StepRunRecord,
    StepStatus,
    TaskHistoryEntry,
    TaskPlan,
    TaskStatus,
)


class TaskStateManager:
    """Maintains task state, step execution records, pause/cancel flags, and history audit logs."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._plans: Dict[str, TaskPlan] = {}
        self._history: Dict[str, List[TaskHistoryEntry]] = {}
        self._run_records: Dict[str, List[StepRunRecord]] = {}
        self._pause_flags: Dict[str, bool] = {}
        self._cancel_flags: Dict[str, bool] = {}

    def save_plan(self, plan: TaskPlan) -> None:
        """Store or update a task plan."""
        with self._lock:
            updated = plan.model_copy(update={"updated_at": datetime.now(timezone.utc)})
            self._plans[plan.task_id] = updated
            if plan.task_id not in self._history:
                self._history[plan.task_id] = []
                self.add_history(plan.task_id, "task_created", details={"objective": plan.objective})

    def get_plan(self, task_id: str) -> Optional[TaskPlan]:
        """Retrieve task plan by task_id."""
        with self._lock:
            return self._plans.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update overall task status with transition audit log."""
        with self._lock:
            plan = self._plans.get(task_id)
            if not plan:
                return False
            old_status = plan.status
            plan = plan.model_copy(
                update={"status": status, "updated_at": datetime.now(timezone.utc)}
            )
            self._plans[task_id] = plan
            self.add_history(
                task_id,
                "status_transition",
                details={"from": old_status.value, "to": status.value},
            )
            return True

    def update_step(self, task_id: str, step_id: str, updates: Dict[str, Any]) -> bool:
        """Update fields of an individual step in the task plan."""
        with self._lock:
            plan = self._plans.get(task_id)
            if not plan:
                return False

            updated_steps = []
            found = False
            for step in plan.steps:
                if step.id == step_id:
                    found = True
                    step = step.model_copy(update=updates)
                updated_steps.append(step)

            if not found:
                return False

            self._plans[task_id] = plan.model_copy(
                update={"steps": updated_steps, "updated_at": datetime.now(timezone.utc)}
            )
            return True

    def add_history(
        self,
        task_id: str,
        event_type: str,
        step_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit log event to the task history."""
        with self._lock:
            entry = TaskHistoryEntry(
                task_id=task_id,
                event_type=event_type,
                step_id=step_id,
                details=details or {},
            )
            if task_id not in self._history:
                self._history[task_id] = []
            self._history[task_id].append(entry)

    def get_history(self, task_id: Optional[str] = None) -> List[TaskHistoryEntry]:
        """Retrieve chronological history for a task, or across all tasks if task_id is None."""
        with self._lock:
            if task_id:
                return list(self._history.get(task_id, []))
            all_entries: List[TaskHistoryEntry] = []
            for entries in self._history.values():
                all_entries.extend(entries)
            all_entries.sort(key=lambda e: e.timestamp)
            return all_entries

    def add_run_record(self, task_id: str, record: StepRunRecord) -> None:
        """Record an attempt/run record for a step."""
        with self._lock:
            if task_id not in self._run_records:
                self._run_records[task_id] = []
            self._run_records[task_id].append(record)

    def get_run_records(self, task_id: str, step_id: Optional[str] = None) -> List[StepRunRecord]:
        """Retrieve run records for a task, optionally filtered by step_id."""
        with self._lock:
            records = self._run_records.get(task_id, [])
            if step_id:
                return [r for r in records if r.step_id == step_id]
            return list(records)

    def pause_task(self, task_id: str) -> bool:
        """Flag task as paused."""
        with self._lock:
            plan = self._plans.get(task_id)
            if not plan or plan.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False
            self._pause_flags[task_id] = True
            self.update_task_status(task_id, TaskStatus.PAUSED)
            self.add_history(task_id, "task_paused")
            return True

    def resume_task(self, task_id: str) -> bool:
        """Unset pause flag and mark task running."""
        with self._lock:
            plan = self._plans.get(task_id)
            if not plan or plan.status != TaskStatus.PAUSED:
                return False
            self._pause_flags[task_id] = False
            self.update_task_status(task_id, TaskStatus.RUNNING)
            self.add_history(task_id, "task_resumed")
            return True

    def is_paused(self, task_id: str) -> bool:
        """Check if task is paused."""
        with self._lock:
            return self._pause_flags.get(task_id, False)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel task and mark pending steps cancelled."""
        with self._lock:
            plan = self._plans.get(task_id)
            if not plan or plan.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False
            self._cancel_flags[task_id] = True
            # Mark all non-completed steps as CANCELLED
            updated_steps = []
            for step in plan.steps:
                if step.status in (StepStatus.PENDING, StepStatus.READY, StepStatus.RUNNING):
                    step = step.model_copy(update={"status": StepStatus.CANCELLED})
                updated_steps.append(step)
            plan = plan.model_copy(
                update={"steps": updated_steps, "status": TaskStatus.CANCELLED, "updated_at": datetime.now(timezone.utc)}
            )
            self._plans[task_id] = plan
            self.add_history(task_id, "task_cancelled")
            return True

    def is_cancelled(self, task_id: str) -> bool:
        """Check if task has been cancelled."""
        with self._lock:
            return self._cancel_flags.get(task_id, False)

    def list_tasks(self) -> List[TaskPlan]:
        """List all managed task plans."""
        with self._lock:
            return list(self._plans.values())

    def list_all_plans(self) -> List[TaskPlan]:
        """Alias for list_tasks."""
        return self.list_tasks()

    def clear(self) -> None:
        """Clear all stored state (for testing)."""
        with self._lock:
            self._plans.clear()
            self._history.clear()
            self._run_records.clear()
            self._pause_flags.clear()
            self._cancel_flags.clear()


__all__ = ["TaskStateManager"]
