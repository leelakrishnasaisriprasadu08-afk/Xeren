"""Pattern detection and lesson extraction tool."""

from collections import defaultdict
import re
from typing import Any, Dict, List, Optional, Set

from xeren.plugins.experience.schemas import ExperienceItem, LessonItem


class ExperiencePatternTool:
    """Analyzes experience corpus for recurring success/failure patterns and distills actionable lessons."""

    STOPWORDS: Set[str] = {
        "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
        "with", "is", "was", "are", "were", "be", "been", "being", "have", "has",
        "had", "it", "its", "this", "that", "these", "those", "of", "as", "by",
    }

    def detect_patterns(self, experiences: List[ExperienceItem]) -> List[Dict[str, Any]]:
        """Identify behavioral clusters, failure hotspots, and reliable strategies."""
        if not experiences:
            return []

        # Group by (selected_plugin, action)
        clusters: Dict[str, List[ExperienceItem]] = defaultdict(list)
        for item in experiences:
            key = f"{item.selected_plugin or 'general'}:{item.action or 'default'}"
            clusters[key].append(item)

        patterns: List[Dict[str, Any]] = []

        for key, items in clusters.items():
            total = len(items)
            successes = sum(1 for i in items if i.success)
            failures = total - successes
            success_rate = round(successes / total, 2)

            pattern_info = {
                "target": key,
                "total_attempts": total,
                "success_rate": success_rate,
                "success_count": successes,
                "failure_count": failures,
            }

            if total >= 2 and (failures / total) >= 0.50:
                common_reasons = [i.failure_reason for i in items if i.failure_reason]
                pattern_info["pattern_type"] = "high_failure_risk"
                pattern_info["diagnostic"] = (
                    f"Action '{key}' fails frequently ({failures}/{total}). Common reasons: {common_reasons[:2]}"
                )
                patterns.append(pattern_info)
            elif total >= 2 and success_rate >= 0.80:
                pattern_info["pattern_type"] = "high_reliability"
                pattern_info["diagnostic"] = (
                    f"Action '{key}' demonstrates high reliability ({successes}/{total}) with consistent success."
                )
                patterns.append(pattern_info)

        return patterns

    def extract_lessons(
        self, experiences: List[ExperienceItem], min_support: int = 1
    ) -> List[LessonItem]:
        """Extract and synthesize structured lessons from historical experiences."""
        if not experiences:
            return []

        lessons: List[LessonItem] = []
        seen_lessons: Set[str] = set()

        # 1. Collect explicitly recorded lessons and failure lessons
        lesson_groups: Dict[str, List[ExperienceItem]] = defaultdict(list)
        for item in experiences:
            if item.lesson and item.lesson.strip():
                clean_lesson = item.lesson.strip()
                lesson_groups[clean_lesson].append(item)
            elif not item.success and (item.failure_avoidance_advice or item.failure_reason):
                advice = item.failure_avoidance_advice or f"Validate preconditions before running '{item.action or item.selected_plugin}': {item.failure_reason}"
                lesson_groups[advice].append(item)

        for lesson_text, items in lesson_groups.items():
            category = items[0].selected_plugin or "general"
            avg_conf = round(sum(i.confidence for i in items) / len(items), 2)
            lesson_item = LessonItem(
                category=category,
                pattern=f"Observed in {len(items)} execution(s)",
                lesson=lesson_text,
                supporting_experiences_count=len(items),
                confidence=avg_conf,
            )
            lessons.append(lesson_item)
            seen_lessons.add(lesson_text.lower())

        # 2. Synthesize lessons from pattern analysis
        patterns = self.detect_patterns(experiences)
        for p in patterns:
            ptype = p.get("pattern_type")
            target = p.get("target", "general")
            plugin = target.split(":")[0]

            if ptype == "high_failure_risk":
                synth_text = f"Exercise caution when using {target}: high historical failure rate ({p['failure_count']}/{p['total_attempts']})."
                if synth_text.lower() not in seen_lessons:
                    lessons.append(
                        LessonItem(
                            category=plugin,
                            pattern="Frequent failure mode",
                            lesson=synth_text,
                            supporting_experiences_count=p["total_attempts"],
                            confidence=0.85,
                        )
                    )
                    seen_lessons.add(synth_text.lower())
            elif ptype == "high_reliability":
                synth_text = f"Action {target} is a proven strategy with {int(p['success_rate']*100)}% success rate."
                if synth_text.lower() not in seen_lessons:
                    lessons.append(
                        LessonItem(
                            category=plugin,
                            pattern="Proven successful strategy",
                            lesson=synth_text,
                            supporting_experiences_count=p["total_attempts"],
                            confidence=0.90,
                        )
                    )
                    seen_lessons.add(synth_text.lower())

        # Sort descending by support count and confidence
        lessons.sort(
            key=lambda l: (l.supporting_experiences_count, l.confidence), reverse=True
        )
        return lessons
