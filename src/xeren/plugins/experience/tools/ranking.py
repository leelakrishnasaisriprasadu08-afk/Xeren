"""Multi-factor experience ranking and failure avoidance analysis tool."""

import re
from typing import Any, List, Optional, Set, Tuple

from xeren.plugins.experience.schemas import ExperienceItem, FailureWarning


class ExperienceRankingTool:
    """Ranks experiences by relevance + outcome quality + confidence, and extracts failure warnings."""

    STOPWORDS: Set[str] = {
        "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
        "with", "is", "was", "are", "were", "be", "been", "being", "have", "has",
        "had", "it", "its", "this", "that", "these", "those", "of", "as", "by",
    }

    def rank_experiences(
        self,
        experiences: List[ExperienceItem],
        task: Optional[str] = None,
        only_reusable: bool = False,
    ) -> Tuple[List[ExperienceItem], List[FailureWarning]]:
        """
        Score, filter, and rank experiences for a given task, extracting failure avoidance warnings.

        Returns:
            (ranked_experiences, failure_warnings)
        """
        if not experiences:
            return [], []

        task_tokens: Set[str] = set()
        if task:
            task_tokens = set(re.findall(r"\w+", task.lower())) - self.STOPWORDS

        scored_items: List[Tuple[ExperienceItem, float, float]] = []
        failure_warnings: List[FailureWarning] = []

        for item in experiences:
            # If only_reusable requested, skip non-reusable items for positive guidance
            if only_reusable and not item.is_reusable:
                continue

            # 1. Relevance calculation
            relevance = 1.0
            if task_tokens:
                item_text = (
                    f"{item.task} {item.selected_plugin or ''} {item.action or ''} "
                    f"{item.lesson or ''} {item.failure_reason or ''} "
                    f"{item.failure_avoidance_advice or ''} {' '.join(item.tags)} {item.context or ''}"
                )
                item_tokens = set(re.findall(r"\w+", item_text.lower())) - self.STOPWORDS
                overlap = task_tokens.intersection(item_tokens)
                relevance = len(overlap) / len(task_tokens)

            # 2. Outcome quality calculation
            quality_signals: List[float] = []
            quality_signals.append(1.0 if item.success else 0.0)

            if item.verification_score is not None:
                quality_signals.append(item.verification_score)
            elif item.verification_status:
                status_scores = {
                    "verified": 1.0,
                    "partially_verified": 0.7,
                    "unverifiable": 0.5,
                    "failed": 0.0,
                }
                quality_signals.append(status_scores.get(item.verification_status.lower(), 0.5))

            if item.user_feedback and item.user_feedback.rating is not None:
                rating_norm = (item.user_feedback.rating - 1.0) / 4.0
                quality_signals.append(rating_norm)
            elif item.user_feedback and item.user_feedback.thumbs_up is not None:
                quality_signals.append(1.0 if item.user_feedback.thumbs_up else 0.0)

            quality = sum(quality_signals) / len(quality_signals)

            # 3. Confidence
            confidence = item.confidence

            # 4. Composite ranking score
            composite = 0.40 * relevance + 0.35 * quality + 0.25 * confidence
            scored_items.append((item, composite, relevance))

            # Check if this item provides a relevant failure warning
            if not item.success and relevance >= 0.15:
                failure_warnings.append(
                    FailureWarning(
                        task_similarity=round(relevance, 3),
                        failed_action=item.action,
                        failed_plugin=item.selected_plugin,
                        failure_reason=item.failure_reason or "Execution failed",
                        avoidance_advice=(
                            item.failure_avoidance_advice
                            or f"Avoid repeating action '{item.action or item.selected_plugin}' under similar task conditions."
                        ),
                    )
                )

        # Sort descending by composite score
        scored_items.sort(key=lambda x: x[1], reverse=True)
        ranked_list = [item for item, _, _ in scored_items]

        # Sort failure warnings descending by similarity
        failure_warnings.sort(key=lambda w: w.task_similarity, reverse=True)

        return ranked_list, failure_warnings
