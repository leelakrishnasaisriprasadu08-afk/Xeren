"""Experience retrieval and outcome tracking statistics tool."""

from typing import Any, Dict, List, Optional

from xeren.plugins.experience.schemas import ExperienceItem, ExperienceStats
from xeren.plugins.experience.stores.base import BaseExperienceStore


class ExperienceRetrieverTool:
    """Queries stored experiences and calculates aggregated outcome metrics."""

    def __init__(self, store: BaseExperienceStore) -> None:
        self.store = store

    def retrieve(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[ExperienceItem]:
        """Search experiences matching textual query and metadata filters."""
        return self.store.search(query=query, filters=filters, limit=limit)

    def get_success_history(
        self, limit: int = 10, plugin: Optional[str] = None
    ) -> List[ExperienceItem]:
        """Retrieve verified successful experience records."""
        filters: Dict[str, Any] = {"success": True, "is_reusable": True}
        if plugin:
            filters["selected_plugin"] = plugin
        return self.store.search(filters=filters, limit=limit)

    def get_failure_history(
        self, limit: int = 10, plugin: Optional[str] = None
    ) -> List[ExperienceItem]:
        """Retrieve failed experience records for post-mortem analysis."""
        filters: Dict[str, Any] = {"success": False}
        if plugin:
            filters["selected_plugin"] = plugin
        return self.store.search(filters=filters, limit=limit)

    def get_stats(self) -> ExperienceStats:
        """Calculate overall outcome tracking statistics."""
        all_items = self.store.search(limit=10000)
        if not all_items:
            return ExperienceStats(
                total_count=0,
                success_count=0,
                failure_count=0,
                avg_confidence=0.0,
                plugin_breakdown={},
            )

        total = len(all_items)
        successes = sum(1 for item in all_items if item.success)
        failures = total - successes
        avg_conf = round(sum(item.confidence for item in all_items) / total, 3)

        breakdown: Dict[str, int] = {}
        for item in all_items:
            p_name = item.selected_plugin or "unspecified"
            breakdown[p_name] = breakdown.get(p_name, 0) + 1

        return ExperienceStats(
            total_count=total,
            success_count=successes,
            failure_count=failures,
            avg_confidence=avg_conf,
            plugin_breakdown=breakdown,
        )
