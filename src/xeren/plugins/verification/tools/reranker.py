"""Candidate scoring and reranking tools for verification."""

import re
from typing import Any, Dict, List, Optional, Set

from xeren.plugins.verification.schemas import CandidateItem, EvidenceItem


class ResultRerankerTool:
    """Reranks alternative candidate outputs based on task relevance, grounding, and quality heuristics."""

    STOPWORDS: Set[str] = {
        "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
        "with", "is", "was", "are", "were", "be", "been", "being", "have", "has",
        "had", "it", "its", "this", "that", "these", "those", "of", "as", "by",
    }

    def rerank(
        self,
        candidates: List[CandidateItem],
        task: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        context: Optional[str] = None,
    ) -> List[CandidateItem]:
        """
        Score and sort candidate items in descending order of quality.

        Returns:
            Sorted list of CandidateItem with assigned `.score`.
        """
        if not candidates:
            return []

        task_tokens: Set[str] = set()
        if task:
            task_tokens = set(re.findall(r"\w+", task.lower())) - self.STOPWORDS

        evidence_tokens: Set[str] = set()
        if evidence:
            for item in evidence:
                evidence_tokens.update(re.findall(r"\w+", item.content.lower()))
            evidence_tokens -= self.STOPWORDS

        scored_candidates: List[CandidateItem] = []

        for candidate in candidates:
            content_str = self._to_str(candidate.content)
            cand_tokens = set(re.findall(r"\w+", content_str.lower())) - self.STOPWORDS

            # 1. Base / prior score
            prior_score = candidate.score if candidate.score is not None else 0.5

            # 2. Task relevance score
            relevance_score = 1.0
            if task_tokens:
                overlap = cand_tokens.intersection(task_tokens)
                relevance_score = len(overlap) / len(task_tokens)

            # 3. Evidence grounding score
            grounding_score = 1.0
            if evidence_tokens:
                ev_overlap = cand_tokens.intersection(evidence_tokens)
                grounding_score = len(ev_overlap) / len(cand_tokens) if cand_tokens else 0.0

            # 4. Content length and structural heuristic
            length_score = 1.0
            word_count = len(re.findall(r"\w+", content_str))
            if word_count == 0:
                length_score = 0.0
            elif word_count < 5:
                length_score = 0.4
            elif word_count > 5000:
                length_score = 0.8
            else:
                length_score = 1.0

            # Composite weighted score
            if task and evidence:
                final_score = (
                    0.20 * prior_score
                    + 0.40 * relevance_score
                    + 0.30 * grounding_score
                    + 0.10 * length_score
                )
            elif task:
                final_score = (
                    0.25 * prior_score
                    + 0.55 * relevance_score
                    + 0.20 * length_score
                )
            elif evidence:
                final_score = (
                    0.25 * prior_score
                    + 0.55 * grounding_score
                    + 0.20 * length_score
                )
            else:
                final_score = 0.60 * prior_score + 0.40 * length_score

            final_score = round(min(1.0, max(0.0, final_score)), 3)

            scored_item = candidate.model_copy(
                update={
                    "score": final_score,
                    "metadata": {
                        **candidate.metadata,
                        "rerank_breakdown": {
                            "relevance": round(relevance_score, 3),
                            "grounding": round(grounding_score, 3),
                            "length": round(length_score, 3),
                        },
                    },
                }
            )
            scored_candidates.append(scored_item)

        # Sort descending by score, tie-break on candidate ID
        scored_candidates.sort(key=lambda item: (item.score or 0.0, item.id), reverse=True)
        return scored_candidates

    def _to_str(self, val: Any) -> str:
        if isinstance(val, str):
            return val
        if isinstance(val, (dict, list)):
            import json
            try:
                return json.dumps(val)
            except Exception:
                return str(val)
        return str(val)
