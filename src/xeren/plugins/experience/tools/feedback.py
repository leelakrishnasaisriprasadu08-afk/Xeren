"""User feedback capture and quality recalibration tool."""

from typing import Optional

from xeren.plugins.experience.schemas import ExperienceItem, UserFeedback
from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool


class ExperienceFeedbackTool:
    """Applies user feedback, ratings, and corrections to adjust confidence and reusability."""

    def __init__(
        self,
        store: BaseExperienceStore,
        sanitizer: Optional[ExperienceSanitizerTool] = None,
    ) -> None:
        self.store = store
        self.sanitizer = sanitizer or ExperienceSanitizerTool()

    def apply_feedback(
        self, experience_id: str, feedback: UserFeedback
    ) -> Optional[ExperienceItem]:
        """Attach user feedback to an experience and update its confidence/reusability."""
        item = self.store.get(experience_id)
        if not item:
            return None

        # Sanitize feedback text
        sanitized_comments = self.sanitizer.sanitize_text(feedback.comments)
        sanitized_correction = self.sanitizer.sanitize_text(feedback.corrected_outcome)
        clean_feedback = feedback.model_copy(
            update={
                "comments": sanitized_comments,
                "corrected_outcome": sanitized_correction,
            }
        )

        confidence = item.confidence
        is_reusable = item.is_reusable

        # Negative feedback: demote confidence and revoke reusability
        if (clean_feedback.rating is not None and clean_feedback.rating <= 2) or (
            clean_feedback.thumbs_up is False
        ):
            confidence = min(confidence, 0.30)
            is_reusable = False
        # Positive feedback: reinforce confidence
        elif (clean_feedback.rating is not None and clean_feedback.rating >= 4) or (
            clean_feedback.thumbs_up is True
        ):
            if item.success:
                confidence = min(1.0, confidence + 0.10)
                is_reusable = True

        updated_item = item.model_copy(
            update={
                "user_feedback": clean_feedback,
                "confidence": round(confidence, 3),
                "is_reusable": is_reusable,
            }
        )

        self.store.update(experience_id, updated_item.model_dump(mode="python"))
        return updated_item
