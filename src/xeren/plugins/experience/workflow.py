"""Workflow orchestrator dispatching all 10 experience operations."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set

from xeren.plugins.experience.registry import ExperienceToolRegistry
from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
    FailureWarning,
    LessonItem,
)

logger = logging.getLogger("xeren.plugins.experience.workflow")


class ExperienceWorkflow:
    """Orchestrates structured experience recording, retrieval, ranking, feedback, and pattern extraction."""

    def __init__(self, registry: Optional[ExperienceToolRegistry] = None) -> None:
        self.registry = registry or ExperienceToolRegistry()

    def run(self, input_data: ExperienceInput) -> ExperienceResult:
        """Synchronously route and execute experience operations."""
        start = time.perf_counter()
        op = input_data.operation

        handler_map = {
            ExperienceOperation.EXPERIENCE_RECORD: self._execute_record,
            ExperienceOperation.EXPERIENCE_RETRIEVAL: self._execute_retrieval,
            ExperienceOperation.SUCCESS_HISTORY: self._execute_success_history,
            ExperienceOperation.FAILURE_HISTORY: self._execute_failure_history,
            ExperienceOperation.USER_FEEDBACK: self._execute_user_feedback,
            ExperienceOperation.PATTERN_DETECTION: self._execute_pattern_detection,
            ExperienceOperation.LESSON_EXTRACTION: self._execute_lesson_extraction,
            ExperienceOperation.EXPERIENCE_RANKING: self._execute_ranking,
            ExperienceOperation.FAILURE_AVOIDANCE: self._execute_failure_avoidance,
            ExperienceOperation.OUTCOME_TRACKING: self._execute_outcome_tracking,
        }

        handler = handler_map.get(op)
        if not handler:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return ExperienceResult(
                operation=op,
                success=False,
                error=f"Unsupported experience operation: '{op}'",
                latency_ms=round(elapsed_ms, 2),
            )

        res = handler(input_data)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return res.model_copy(update={"latency_ms": round(elapsed_ms, 2)})

    async def arun(self, input_data: ExperienceInput) -> ExperienceResult:
        """Asynchronously execute experience operations."""
        return await asyncio.to_thread(self.run, input_data)

    # -------------------------------------------------------------------------
    # Handlers
    # -------------------------------------------------------------------------
    def _execute_record(self, input_data: ExperienceInput) -> ExperienceResult:
        item = input_data.item
        if not item:
            if not input_data.task:
                return ExperienceResult(
                    operation=input_data.operation,
                    success=False,
                    error="Task is required when recording an experience item.",
                )
            item = ExperienceItem(
                task=input_data.task,
                context=input_data.context,
                selected_plugin=input_data.plugin_name,
                action=input_data.action,
                outcome=input_data.outcome,
                success=input_data.success if input_data.success is not None else True,
                verification_status=input_data.verification_status,
                verification_score=input_data.verification_score,
                user_feedback=input_data.user_feedback,
                confidence=input_data.confidence,
                lesson=input_data.lesson,
                failure_reason=input_data.failure_reason,
                failure_avoidance_advice=input_data.failure_avoidance_advice,
                error=input_data.error,
                tags=input_data.tags,
                metadata=input_data.metadata,
            )

        saved_item, was_deduplicated = self.registry.recorder_tool.record(item)
        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            item=saved_item,
            metadata={"deduplicated": was_deduplicated},
        )

    def _execute_retrieval(self, input_data: ExperienceInput) -> ExperienceResult:
        filters: Dict[str, Any] = {}
        if input_data.filter_plugin:
            filters["selected_plugin"] = input_data.filter_plugin
        if input_data.success is not None:
            filters["success"] = input_data.success

        raw_items = self.registry.retriever_tool.retrieve(
            query=input_data.task,
            filters=filters if filters else None,
            limit=input_data.limit * 2,
        )

        ranked, warnings = self.registry.ranking_tool.rank_experiences(
            experiences=raw_items,
            task=input_data.task,
            only_reusable=False,
        )

        final_items = ranked[: input_data.limit]
        extracted_lessons = self.registry.pattern_tool.extract_lessons(final_items)
        decision_context = self._format_decision_context(final_items, warnings, extracted_lessons)

        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            experiences=final_items,
            failure_warnings=warnings[:3],
            lessons=extracted_lessons[:5],
            decision_context=decision_context,
        )

    def _execute_success_history(self, input_data: ExperienceInput) -> ExperienceResult:
        items = self.registry.retriever_tool.get_success_history(
            limit=input_data.limit,
            plugin=input_data.filter_plugin,
        )
        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            experiences=items,
        )

    def _execute_failure_history(self, input_data: ExperienceInput) -> ExperienceResult:
        items = self.registry.retriever_tool.get_failure_history(
            limit=input_data.limit,
            plugin=input_data.filter_plugin,
        )
        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            experiences=items,
        )

    def _execute_user_feedback(self, input_data: ExperienceInput) -> ExperienceResult:
        if not input_data.experience_id:
            return ExperienceResult(
                operation=input_data.operation,
                success=False,
                error="experience_id is required to apply user feedback.",
            )
        if not input_data.user_feedback:
            return ExperienceResult(
                operation=input_data.operation,
                success=False,
                error="user_feedback payload is required.",
            )

        updated = self.registry.feedback_tool.apply_feedback(
            experience_id=input_data.experience_id,
            feedback=input_data.user_feedback,
        )
        if not updated:
            return ExperienceResult(
                operation=input_data.operation,
                success=False,
                error=f"Experience with ID '{input_data.experience_id}' not found.",
            )

        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            item=updated,
        )

    def _execute_pattern_detection(self, input_data: ExperienceInput) -> ExperienceResult:
        all_items = self.registry.retriever_tool.retrieve(limit=1000)
        patterns = self.registry.pattern_tool.detect_patterns(all_items)
        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            metadata={"patterns": patterns},
        )

    def _execute_lesson_extraction(self, input_data: ExperienceInput) -> ExperienceResult:
        filters: Dict[str, Any] = {}
        if input_data.filter_plugin:
            filters["selected_plugin"] = input_data.filter_plugin

        items = self.registry.retriever_tool.retrieve(
            query=input_data.task,
            filters=filters if filters else None,
            limit=1000,
        )
        lessons = self.registry.pattern_tool.extract_lessons(items)
        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            lessons=lessons[: input_data.limit],
        )

    def _execute_ranking(self, input_data: ExperienceInput) -> ExperienceResult:
        filters: Dict[str, Any] = {}
        if input_data.filter_plugin:
            filters["selected_plugin"] = input_data.filter_plugin

        items = self.registry.retriever_tool.retrieve(
            query=input_data.task,
            filters=filters if filters else None,
            limit=input_data.limit * 2,
        )
        ranked, warnings = self.registry.ranking_tool.rank_experiences(
            experiences=items,
            task=input_data.task,
        )
        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            experiences=ranked[: input_data.limit],
            failure_warnings=warnings,
        )

    def _execute_failure_avoidance(self, input_data: ExperienceInput) -> ExperienceResult:
        failed_items = self.registry.retriever_tool.get_failure_history(
            limit=50, plugin=input_data.filter_plugin
        )
        _, warnings = self.registry.ranking_tool.rank_experiences(
            experiences=failed_items,
            task=input_data.task,
        )
        filtered_warnings = warnings[: input_data.limit]

        context_lines = []
        if filtered_warnings:
            context_lines.append("### FAILURE AVOIDANCE WARNINGS (FROM PAST EXPERIENCES):")
            for w in filtered_warnings:
                context_lines.append(
                    f"- Action '{w.failed_action or w.failed_plugin}' failed previously: {w.failure_reason}. Advice: {w.avoidance_advice}"
                )

        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            failure_warnings=filtered_warnings,
            decision_context="\n".join(context_lines) if context_lines else None,
        )

    def _execute_outcome_tracking(self, input_data: ExperienceInput) -> ExperienceResult:
        stats = self.registry.retriever_tool.get_stats()
        return ExperienceResult(
            operation=input_data.operation,
            success=True,
            stats=stats,
        )

    def _format_decision_context(
        self,
        experiences: List[ExperienceItem],
        warnings: List[FailureWarning],
        lessons: Optional[List[LessonItem]] = None,
    ) -> Optional[str]:
        """Format a clean markdown guidance block for the Core planning LLM."""
        sections: List[str] = []

        # 1. Failure warnings first (highest priority: avoid repeating mistakes)
        if warnings:
            sections.append("### PAST FAILURE WARNINGS (AVOID THESE MISTAKES):")
            for w in warnings[:3]:
                sections.append(
                    f"- Warning (relevance: {w.task_similarity:.2f}): {w.failure_reason}. Avoidance Advice: {w.avoidance_advice}"
                )

        # 2. Reusable lessons learned
        if lessons:
            sections.append("### RELEVANT LESSONS LEARNED:")
            for l in lessons[:3]:
                sections.append(f"- [{l.category}] {l.lesson}")
        else:
            seen_l: Set[str] = set()
            exp_lessons: List[str] = []
            for e in experiences:
                if e.lesson and e.lesson.strip() and e.lesson.strip().lower() not in seen_l:
                    seen_l.add(e.lesson.strip().lower())
                    category = e.selected_plugin or "general"
                    exp_lessons.append(f"- [{category}] {e.lesson.strip()}")
            if exp_lessons:
                sections.append("### RELEVANT LESSONS LEARNED:")
                sections.extend(exp_lessons[:3])

        # 3. Top verified successes
        reusable_successes = [e for e in experiences if e.success and e.is_reusable][:3]
        if reusable_successes:
            sections.append("### SUCCESSFUL PREVIOUS STRATEGIES:")
            for e in reusable_successes:
                lesson_str = f" | Lesson: {e.lesson}" if e.lesson else ""
                sections.append(
                    f"- Task: '{e.task[:80]}' -> Used {e.selected_plugin}:{e.action}{lesson_str}"
                )

        return "\n".join(sections) if sections else None


__all__ = ["ExperienceWorkflow"]
