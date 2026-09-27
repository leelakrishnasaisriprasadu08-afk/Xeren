"""
LLMPathClassifier — Uses the Xeren LLM to evaluate file content/metadata
and route the file into the correct security vault tier:

  LIBERAL       →  ~/.xeren/vault/liberal/
  SENSITIVE     →  ~/.xeren/vault/sensitive/
  MORE_SENSITIVE→  ~/.xeren/vault/over_sensitive/

The LLM is asked to reason about the file's contents before classifying.
The XerenSecurityGate enforces access rules after classification.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from xeren.security.schemas import DataSensitivityTier
from xeren.security.gate import XerenSecurityGate

if TYPE_CHECKING:
    from xeren.models.base import BaseLLM

logger = logging.getLogger("xeren.security.path_classifier")


# ─────────────────────────────────────────────────────────────────────────────
# Vault Paths
# ─────────────────────────────────────────────────────────────────────────────

VAULT_ROOT = Path.home() / ".xeren" / "vault"

TIER_PATHS = {
    DataSensitivityTier.LIBERAL:        VAULT_ROOT / "liberal",
    DataSensitivityTier.SENSITIVE:      VAULT_ROOT / "sensitive",
    DataSensitivityTier.MORE_SENSITIVE: VAULT_ROOT / "over_sensitive",
}

# Description hints for each tier (used in LLM classification prompt)
TIER_DESCRIPTIONS = {
    DataSensitivityTier.LIBERAL: (
        "LIBERAL — public or non-sensitive data: code files, notes, logs, "
        "config files, public documents, general reports."
    ),
    DataSensitivityTier.SENSITIVE: (
        "SENSITIVE — personal or client data: photos, contact lists, "
        "project specs, private messages, credentials references, work briefs."
    ),
    DataSensitivityTier.MORE_SENSITIVE: (
        "MORE_SENSITIVE — critical private data: government IDs, passports, "
        "bank statements, private keys, legal contracts, PAN/Aadhaar numbers, "
        "financial records, confidential client information."
    ),
}

# Heuristic keyword signals (fast pre-filter before calling LLM)
_LIBERAL_SIGNALS = {".log", ".md", ".txt", ".json", ".yaml", ".toml", ".py", ".js", ".ts"}
_OVER_SENSITIVE_SIGNALS = {
    "aadhaar", "pan", "passport", "ssn", "private key", "secret key",
    "bank statement", "credit card", "cvv", "-----begin", "legal contract",
}
_SENSITIVE_SIGNALS = {
    "password", "token", "api_key", "apikey", "client_id", "client_secret",
    "brief", "proposal", "invoice", "personal", "confidential",
}


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic pre-filter (fast path, no LLM call needed)
# ─────────────────────────────────────────────────────────────────────────────

def _heuristic_classify(file_path: str, content: str) -> Optional[DataSensitivityTier]:
    """
    Fast keyword-based pre-classification.
    Returns a tier if confident, or None to fall through to LLM classification.
    """
    content_lower = content.lower()
    ext = Path(file_path).suffix.lower()

    # Check for over-sensitive signals first (highest priority)
    if any(sig in content_lower for sig in _OVER_SENSITIVE_SIGNALS):
        return DataSensitivityTier.MORE_SENSITIVE

    # Then sensitive
    if any(sig in content_lower for sig in _SENSITIVE_SIGNALS):
        return DataSensitivityTier.SENSITIVE

    # Extension-based liberal fast path (only if no sensitive signals found)
    if ext in _LIBERAL_SIGNALS and len(content) < 5000:
        return DataSensitivityTier.LIBERAL

    return None  # unclear — send to LLM


# ─────────────────────────────────────────────────────────────────────────────
# LLM Classifier
# ─────────────────────────────────────────────────────────────────────────────

class LLMPathClassifier:
    """
    Classifies files using the local Xeren LLM and routes them into the
    appropriate security vault path.

    Workflow:
      1. Heuristic pre-filter (instant, no LLM call).
      2. If unclear → ask LLM to reason about the content and classify.
      3. Gate the final decision through XerenSecurityGate.
      4. Copy the file into the appropriate vault sub-directory.
    """

    def __init__(
        self,
        llm: "BaseLLM",
        security_gate: Optional[XerenSecurityGate] = None,
        vault_root: Optional[Path] = None,
    ) -> None:
        self.llm = llm
        self.security_gate = security_gate or XerenSecurityGate()
        self.vault_root = vault_root or VAULT_ROOT
        # Ensure vault directories exist
        for vault_path in TIER_PATHS.values():
            vault_path.mkdir(parents=True, exist_ok=True)
        logger.info("LLMPathClassifier ready. Vault root: %s", self.vault_root)

    # ── Public API ───────────────────────────────────────────────────────────

    def classify(self, file_path: str, content: str) -> DataSensitivityTier:
        """
        Classify file content into a security tier.

        Steps:
          1. Heuristic pre-filter.
          2. LLM classification if heuristic is inconclusive.
          3. Return the tier.
        """
        # Step 1 — fast heuristic
        heuristic_tier = _heuristic_classify(file_path, content)
        if heuristic_tier is not None:
            logger.info(
                "[classify] Heuristic → %s for '%s'",
                heuristic_tier.value, file_path
            )
            return heuristic_tier

        # Step 2 — LLM classification
        return self._llm_classify(file_path, content)

    def classify_and_store(
        self,
        path: str,
        content: str,
        user_id: str = "system",
    ) -> DataSensitivityTier:
        """
        Classify the file AND copy it into the correct vault directory.
        Returns the assigned DataSensitivityTier.
        """
        tier = self.classify(path, content)
        self._store_in_vault(path, content, tier, user_id)
        return tier

    # ── LLM Classification ───────────────────────────────────────────────────

    def _llm_classify(self, file_path: str, content: str) -> DataSensitivityTier:
        """Ask the LLM to reason about the file and return one of the three tiers."""
        from xeren.models.types import ChatMessage

        # Truncate content for the prompt (avoid token overflow)
        content_preview = content[:800] if len(content) > 800 else content

        tier_descriptions = "\n".join(
            f"  {tier.value.upper()}: {desc}"
            for tier, desc in TIER_DESCRIPTIONS.items()
        )

        classification_prompt = (
            "You are Xeren's security classification engine.\n"
            "Evaluate the file below and classify it into EXACTLY ONE tier.\n\n"
            f"Available tiers:\n{tier_descriptions}\n\n"
            f"File path: {file_path}\n"
            f"File content preview:\n```\n{content_preview}\n```\n\n"
            "Respond with ONLY one word — the tier name in lowercase: "
            "liberal | sensitive | more_sensitive\n"
            "Do not add any explanation. Just the tier name."
        )

        messages = [
            ChatMessage.system(
                "You are Xeren's strict data security classification engine. "
                "You respond with exactly one word: the security tier."
            ),
            ChatMessage.user(classification_prompt),
        ]

        try:
            response = self.llm.generate(messages, max_new_tokens=10, temperature=0.0)
            raw = response.content.strip().lower().split()[0] if response.content.strip() else ""

            tier_map = {
                "liberal":        DataSensitivityTier.LIBERAL,
                "sensitive":      DataSensitivityTier.SENSITIVE,
                "more_sensitive": DataSensitivityTier.MORE_SENSITIVE,
                "over_sensitive": DataSensitivityTier.MORE_SENSITIVE,  # alias
            }
            tier = tier_map.get(raw)
            if tier:
                logger.info("[classify] LLM → %s for '%s'", tier.value, file_path)
                return tier
            else:
                logger.warning(
                    "[classify] LLM returned unexpected tier '%s' — defaulting to SENSITIVE",
                    raw,
                )
                return DataSensitivityTier.SENSITIVE

        except Exception as exc:
            logger.error("[classify] LLM classification failed: %s — defaulting to SENSITIVE", exc)
            return DataSensitivityTier.SENSITIVE

    # ── Vault Storage ────────────────────────────────────────────────────────

    def _store_in_vault(
        self,
        source_path: str,
        content: str,
        tier: DataSensitivityTier,
        user_id: str,
    ) -> Path:
        """
        Write (or copy) a file into the correct vault sub-directory.
        Verifies access via the XerenSecurityGate before writing.
        """
        vault_dir = TIER_PATHS[tier]
        file_name = Path(source_path).name
        dest_path = vault_dir / file_name

        # Gate check — verify we're allowed to write here
        gate_decision = self.security_gate.check_access(
            path=dest_path,
            operation="write",
            user_id=user_id,
            user_intent=f"LLM-classified file storage into {tier.value} vault",
            tier_override=tier,
        )

        if not gate_decision.is_allowed:
            logger.warning(
                "[store] Security gate blocked write to %s: %s",
                dest_path, gate_decision.reason,
            )
            # Still write to liberal as fallback (no sensitive data goes untracked)
            dest_path = TIER_PATHS[DataSensitivityTier.LIBERAL] / file_name

        dest_path.write_text(content, encoding="utf-8")
        logger.info(
            "[store] '%s' stored → %s (tier=%s)",
            file_name, dest_path, tier.value,
        )
        return dest_path

    def get_vault_path(self, tier: DataSensitivityTier) -> Path:
        """Return the vault directory for a given tier."""
        return TIER_PATHS[tier]

    def list_vault_contents(self) -> dict:
        """Return a summary of files in each vault tier."""
        return {
            tier.value: [f.name for f in TIER_PATHS[tier].glob("*") if f.is_file()]
            for tier in DataSensitivityTier
        }


__all__ = ["LLMPathClassifier", "TIER_PATHS", "VAULT_ROOT"]
