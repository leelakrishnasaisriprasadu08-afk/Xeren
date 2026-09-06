"""Experience recording, sanitization, quality filtering, and deduplication tool."""

from datetime import datetime, timezone
from typing import Optional, Tuple

from xeren.plugins.experience.schemas import ExperienceItem
from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool


class ExperienceRecorderTool:
    """Safely sanitizes, deduplicates, and records structured execution experiences."""

    def __init__(
        self,
        store: BaseExperienceStore,
        sanitizer: Optional[ExperienceSanitizerTool] = None,
    ) -> None:
        self.store = store
        self.sanitizer = sanitizer or ExperienceSanitizerTool()

    def record(self, item: ExperienceItem) -> Tuple[ExperienceItem, bool]:
        """
        Sanitize, quality-filter, deduplicate, and persist an experience item.

        Returns:
            (saved_item, was_deduplicated)
        """
        # 1. Sanitize all textual and structural fields
        sanitized_task = self.sanitizer.sanitize_text(item.task) or ""
        sanitized_context = self.sanitizer.sanitize_text(item.context)
        sanitized_action = self.sanitizer.sanitize_text(item.action)
        sanitized_outcome = self.sanitizer.sanitize_payload(item.outcome)
        sanitized_lesson = self.sanitizer.sanitize_text(item.lesson)
        sanitized_failure = self.sanitizer.sanitize_text(item.failure_reason)
        sanitized_advice = self.sanitizer.sanitize_text(item.failure_avoidance_advice)
        sanitized_error = self.sanitizer.sanitize_text(item.error)
        sanitized_meta = self.sanitizer.sanitize_payload(item.metadata)

        # If failure_reason missing but error present, adopt error
        if not sanitized_failure and sanitized_error:
            sanitized_failure = sanitized_error

        # 2. Reusability evaluation
        is_reusable = item.is_reusable
        if not item.success or item.verification_status == "failed":
            is_reusable = False
        elif (
            item.user_feedback
            and item.user_feedback.rating is not None
            and item.user_feedback.rating <= 2
        ):
            is_reusable = False
        elif (
            item.user_feedback
            and item.user_feedback.thumbs_up is False
        ):
            is_reusable = False
        elif item.success:
            if item.verification_status == "verified" and item.confidence >= 0.50:
                is_reusable = True
            elif item.verification_status == "partially_verified" and item.confidence >= 0.60:
                is_reusable = True
            elif item.user_feedback and (
                (item.user_feedback.rating is not None and item.user_feedback.rating >= 4)
                or item.user_feedback.thumbs_up is True
            ):
                is_reusable = True
            elif item.confidence >= 0.75 and item.verification_status != "unverifiable":
                is_reusable = True
            else:
                is_reusable = False

        # 3. Auto-synthesize failure avoidance advice if missing
        if not item.success and not sanitized_advice:
            reason = sanitized_failure or sanitized_error or "unspecified execution failure"
            action = sanitized_action or item.selected_plugin or "this action"
            sanitized_advice = f"Ensure preconditions are validated to avoid '{reason}' when executing action '{action}'."

        # 4. Auto-synthesize actionable lesson if missing
        if not sanitized_lesson:
            if not item.success:
                if sanitized_advice:
                    sanitized_lesson = sanitized_advice
                elif sanitized_failure:
                    sanitized_lesson = f"Validate requirements before executing '{sanitized_action or item.selected_plugin}': {sanitized_failure}."
            elif item.success and is_reusable:
                sanitized_lesson = f"Strategy '{item.selected_plugin or 'general'}:{sanitized_action or 'execute'}' was effective for: {sanitized_task[:80]}."

        clean_item = item.model_copy(
            update={
                "task": sanitized_task,
                "context": sanitized_context,
                "action": sanitized_action,
                "outcome": sanitized_outcome,
                "lesson": sanitized_lesson,
                "failure_reason": sanitized_failure,
                "failure_avoidance_advice": sanitized_advice,
                "error": sanitized_error,
                "is_reusable": is_reusable,
                "metadata": sanitized_meta,
            }
        )

        # 4. Deduplication via content fingerprint
        fp = clean_item.generate_fingerprint()
        clean_item = clean_item.model_copy(update={"content_fingerprint": fp})

        existing = self.store.get_by_fingerprint(fp)
        if existing:
            occurrences = int(existing.metadata.get("occurrence_count", 1)) + 1
            updated_meta = {**existing.metadata, "occurrence_count": occurrences}
            updated_item = existing.model_copy(
                update={
                    "timestamp": datetime.now(timezone.utc),
                    "confidence": max(existing.confidence, clean_item.confidence),
                    "metadata": updated_meta,
                }
            )
            self.store.update(existing.id, updated_item.model_dump(mode="python"))
            return updated_item, True

        # 5. Store new experience
        self.store.add(clean_item)
        return clean_item, False
