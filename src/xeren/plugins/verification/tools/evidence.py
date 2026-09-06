"""Source evidence grounding and fact-checking verification tools."""

import re
from typing import Any, Dict, List, Set, Tuple

from xeren.plugins.verification.schemas import CheckResult, EvidenceItem, VerificationOperation


class SourceEvidenceTool:
    """Evaluates factual claims and candidate grounding against source evidence."""

    STOPWORDS: Set[str] = {
        "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
        "with", "is", "was", "are", "were", "be", "been", "being", "have", "has",
        "had", "it", "its", "this", "that", "these", "those", "of", "as", "by",
    }

    def verify_evidence(
        self,
        candidate: Any,
        evidence: List[EvidenceItem],
        operation: VerificationOperation,
    ) -> Tuple[List[CheckResult], float, Dict[str, Any], List[str], bool]:
        """
        Verify factual claims against evidence.

        Returns:
            (checks, grounding_score, provenance, unsupported_claims, is_unverifiable)
        """
        checks: List[CheckResult] = []
        provenance: Dict[str, Any] = {}
        unsupported_claims: List[str] = []

        # 1. Evidence availability check
        if not evidence:
            if operation in (VerificationOperation.FACT_CHECKING, VerificationOperation.SOURCE_EVIDENCE_CHECK):
                checks.append(
                    CheckResult(
                        name="evidence_availability",
                        passed=False,
                        score=0.0,
                        reason="No source evidence provided to ground or verify factual claims.",
                        actionable_correction="Provide authoritative source evidence or retrieved documents.",
                    )
                )
                return checks, 0.0, provenance, unsupported_claims, True
            else:
                # Other operations might not strictly require evidence
                return checks, 1.0, provenance, unsupported_claims, False

        checks.append(
            CheckResult(
                name="evidence_availability",
                passed=True,
                score=1.0,
                reason=f"Found {len(evidence)} evidence sources for grounding verification.",
            )
        )

        candidate_text = candidate if isinstance(candidate, str) else str(candidate)
        sentences = self._split_sentences(candidate_text)

        if not sentences:
            checks.append(
                CheckResult(
                    name="grounding_faithfulness_check",
                    passed=True,
                    score=1.0,
                    reason="Candidate text has no factual claims.",
                )
            )
            return checks, 1.0, provenance, unsupported_claims, False

        # Index evidence tokens & n-grams
        evidence_index: List[Dict[str, Any]] = []
        all_evidence_tokens: Set[str] = set()
        all_evidence_bigrams: Set[str] = set()

        for item in evidence:
            tokens = self._tokenize(item.content)
            bigrams = self._extract_ngrams(tokens, 2)
            evidence_index.append(
                {
                    "item": item,
                    "tokens": set(tokens),
                    "bigrams": bigrams,
                }
            )
            all_evidence_tokens.update(tokens)
            all_evidence_bigrams.update(bigrams)

        sentence_scores: List[float] = []
        supported_claim_count = 0

        for sentence in sentences:
            s_tokens = self._tokenize(sentence)
            if not s_tokens:
                continue

            content_tokens = [t for t in s_tokens if t not in self.STOPWORDS]
            if not content_tokens:
                # Pure filler sentence
                continue

            s_set = set(content_tokens)
            overlap = s_set.intersection(all_evidence_tokens)
            token_ratio = len(overlap) / len(s_set) if s_set else 0.0

            # Bigram overlap for phrases
            s_bigrams = self._extract_ngrams(s_tokens, 2)
            bigram_ratio = 0.0
            if s_bigrams:
                b_overlap = s_bigrams.intersection(all_evidence_bigrams)
                bigram_ratio = len(b_overlap) / len(s_bigrams)

            # Combined grounding score for this sentence
            score = 0.6 * token_ratio + 0.4 * bigram_ratio
            sentence_scores.append(score)

            # Determine supporting sources for provenance
            supporting_sources = []
            for ev in evidence_index:
                ev_tokens = ev["tokens"]
                ev_overlap = s_set.intersection(ev_tokens)
                if len(ev_overlap) >= 2 or (len(s_set) == 1 and len(ev_overlap) == 1):
                    supporting_sources.append(ev["item"].source_id)

            if score >= 0.25:
                supported_claim_count += 1
                provenance[sentence[:80]] = supporting_sources
            else:
                unsupported_claims.append(sentence)

        grounding_score = (
            sum(sentence_scores) / len(sentence_scores) if sentence_scores else 1.0
        )
        grounding_score = round(min(1.0, max(0.0, grounding_score)), 3)

        # 2. Grounding faithfulness check
        is_grounded = grounding_score >= 0.45 and len(unsupported_claims) <= len(sentences) // 2
        checks.append(
            CheckResult(
                name="grounding_faithfulness_check",
                passed=is_grounded,
                score=grounding_score,
                reason=f"Evidence grounding score is {grounding_score:.2f} across {len(sentences)} claims.",
                actionable_correction="Ensure statements are substantiated by the provided reference evidence." if not is_grounded else None,
                details={
                    "grounding_score": grounding_score,
                    "supported_claims": supported_claim_count,
                    "total_claims": len(sentences),
                },
            )
        )

        # 3. Unsupported claims check
        if unsupported_claims:
            checks.append(
                CheckResult(
                    name="unsupported_claims_check",
                    passed=False,
                    score=max(0.0, 1.0 - len(unsupported_claims) / max(len(sentences), 1)),
                    reason=f"Detected {len(unsupported_claims)} claims without clear evidence support.",
                    actionable_correction=f"Substantiate or remove unsupported claim: '{unsupported_claims[0]}'",
                    details={"unsupported_claims": unsupported_claims},
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="unsupported_claims_check",
                    passed=True,
                    score=1.0,
                    reason="All evaluated claims are grounded in provided evidence.",
                )
            )

        # 4. Citation check
        citation_check = self._check_citations(candidate_text, evidence)
        checks.append(citation_check)

        return checks, grounding_score, provenance, unsupported_claims, False

    def _check_citations(self, text: str, evidence: List[EvidenceItem]) -> CheckResult:
        evidence_ids = {item.source_id.lower() for item in evidence}
        # Find citation markers like [source_id] or [1] or (Source: XYZ)
        bracket_cits = re.findall(r"\[([a-zA-Z0-9_\-\.:]+)\]", text)
        if not bracket_cits:
            return CheckResult(
                name="citation_validity_check",
                passed=True,
                score=1.0,
                reason="No explicit bracket citations present in candidate.",
            )

        valid_cits = []
        invalid_cits = []
        for cit in bracket_cits:
            if cit.lower() in evidence_ids or cit.isdigit():
                valid_cits.append(cit)
            else:
                invalid_cits.append(cit)

        if invalid_cits:
            return CheckResult(
                name="citation_validity_check",
                passed=False,
                score=len(valid_cits) / len(bracket_cits),
                reason=f"Citations do not match provided evidence sources: {invalid_cits}",
                actionable_correction=f"Use real evidence source IDs in citations: {sorted(list(evidence_ids))}",
                details={"invalid_citations": invalid_cits, "valid_citations": valid_cits},
            )

        return CheckResult(
            name="citation_validity_check",
            passed=True,
            score=1.0,
            reason=f"All {len(valid_cits)} citation markers correspond to valid evidence sources.",
        )

    def _split_sentences(self, text: str) -> List[str]:
        # Split on sentence terminals while avoiding decimals/abbreviations
        raw = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in raw if len(s.strip()) > 3]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _extract_ngrams(self, tokens: List[str], n: int) -> Set[str]:
        return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}
