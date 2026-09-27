"""Data sensitivity auto-classifier — detects the right tier for any file or content."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, Optional

from xeren.security.schemas import DataSensitivityTier

logger = logging.getLogger("xeren.security.classification")


# ---------------------------------------------------------------------------
# Keyword & Pattern Libraries
# ---------------------------------------------------------------------------

# More Sensitive: Government IDs, financial, legal, business-critical
_MORE_SENSITIVE_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"aadhaar|aadhar|uid_card", re.IGNORECASE),
    re.compile(r"pan[_\s-]?card|pan[_\s-]?no", re.IGNORECASE),
    re.compile(r"passport", re.IGNORECASE),
    re.compile(r"voter[_\s-]?id|election[_\s-]?card", re.IGNORECASE),
    re.compile(r"driving[_\s-]?licen[cs]e|dl[_\s-]?copy", re.IGNORECASE),
    re.compile(r"bank[_\s-]?statement|account[_\s-]?statement", re.IGNORECASE),
    re.compile(r"salary[_\s-]?slip|pay[_\s-]?slip|payroll", re.IGNORECASE),
    re.compile(r"(income[_\s-]?)?tax[_\s-]?(return|filing)|form[_\s-]?16", re.IGNORECASE),
    re.compile(r"gst[_\s-]?certificate|gstin", re.IGNORECASE),
    re.compile(r"(non[_\s-]?disclosure|nda|confidential)[_\s-]?agreement", re.IGNORECASE),
    re.compile(r"(legal|court)[_\s-]?(notice|order|document)", re.IGNORECASE),
    re.compile(r"trade[_\s-]?secret|proprietary", re.IGNORECASE),
    re.compile(r"business[_\s-]?contract|service[_\s-]?agreement", re.IGNORECASE),
    re.compile(r"insurance[_\s-]?(policy|claim)", re.IGNORECASE),
    re.compile(r"demat|mutual[_\s-]?fund|portfolio[_\s-]?statement", re.IGNORECASE),
    re.compile(r"private[_\s-]?key|secret|credential|token|api[_\s-]?key", re.IGNORECASE),
    re.compile(r"\.(pem|key|pfx|p12|kdbx|env)$", re.IGNORECASE),
]

_MORE_SENSITIVE_FOLDER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(^|[/\\])(legal|contracts|agreements|nda)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(financial|finance|banking|accounts)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(government|govt|kyc|identity)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(confidential|secret|private)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(tax|itr|gst)([/\\]|$)", re.IGNORECASE),
]

# Sensitive: Personal data, media, contacts, health
_SENSITIVE_EXTENSIONS: frozenset[str] = frozenset({
    # Photos & videos
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".raw", ".cr2",
    ".mp4", ".mov", ".avi", ".mkv", ".m4v",
    # Contacts & calendar
    ".vcf", ".ics",
    # Personal audio
    ".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac",
})

_SENSITIVE_FOLDER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(^|[/\\])(pictures?|photos?|camera|gallery|images?)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(videos?|movies?|recordings?)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(contacts?|address[_\s-]?book)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(medical|health|clinic|hospital|prescription)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(personal|private|diary|journal)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(messages?|chat|whatsapp|telegram)([/\\]|$)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(hr|human[_\s-]?resource|employee)([/\\]|$)", re.IGNORECASE),
]

_SENSITIVE_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"medical[_\s-]?(record|report|history)", re.IGNORECASE),
    re.compile(r"prescription|diagnosis|lab[_\s-]?report", re.IGNORECASE),
    re.compile(r"personal[_\s-]?diary|journal", re.IGNORECASE),
    re.compile(r"contact[_\s-]?(list|book|backup)", re.IGNORECASE),
]


class DataClassifier:
    """
    Automatically classifies files or content into sensitivity tiers.

    Classification priority:
      1. User override (always wins — stored in UserVault)
      2. More Sensitive patterns (filename, folder path)
      3. Sensitive patterns (extension, folder, filename)
      4. Default: Liberal
    """

    def __init__(self) -> None:
        # In-memory cache of user overrides: path_str -> tier
        # These are loaded from UserVault at session start
        self._overrides: Dict[str, DataSensitivityTier] = {}

    # -----------------------------------------------------------------------
    # User Overrides
    # -----------------------------------------------------------------------

    def set_override(self, path: str, tier: DataSensitivityTier) -> None:
        """Store a user-specified tier override for a path (or prefix)."""
        normalized = Path(path).as_posix().lower()
        self._overrides[normalized] = tier
        logger.info("User override set: '%s' → %s", normalized, tier.value)

    def remove_override(self, path: str) -> bool:
        """Remove a user override, reverting to auto-classification."""
        normalized = Path(path).as_posix().lower()
        if normalized in self._overrides:
            del self._overrides[normalized]
            logger.info("User override removed: '%s'", normalized)
            return True
        return False

    def get_override(self, path: str) -> Optional[DataSensitivityTier]:
        """Return user override for a path, or None if none set."""
        normalized = Path(path).as_posix().lower()
        # Exact match first
        if normalized in self._overrides:
            return self._overrides[normalized]
        # Prefix match — if a parent folder has an override
        for override_path, tier in self._overrides.items():
            if normalized.startswith(override_path):
                return tier
        return None

    def load_overrides(self, overrides: Dict[str, DataSensitivityTier]) -> None:
        """Bulk-load overrides from UserVault at session start."""
        self._overrides = {Path(k).as_posix().lower(): v for k, v in overrides.items()}

    # -----------------------------------------------------------------------
    # Classification
    # -----------------------------------------------------------------------

    def classify(
        self,
        path: Path | str,
        user_override: Optional[DataSensitivityTier] = None,
    ) -> DataSensitivityTier:
        """
        Classify a file path into a sensitivity tier.

        Args:
            path: The file or directory path to classify (Path or str).
            user_override: Explicit override — always wins if provided.

        Returns:
            DataSensitivityTier
        """
        if isinstance(path, str):
            path = Path(path)
        # 1. Explicit argument override (highest priority)
        if user_override is not None:
            return user_override

        # 2. Stored user override (from vault)
        stored = self.get_override(str(path))
        if stored is not None:
            return stored

        path_str = str(path).replace("\\", "/")
        name = path.name

        # 3. Check More Sensitive — filename patterns
        for pattern in _MORE_SENSITIVE_NAME_PATTERNS:
            if pattern.search(name):
                logger.debug("More Sensitive (filename pattern): %s", name)
                return DataSensitivityTier.MORE_SENSITIVE

        # 4. Check More Sensitive — folder path patterns
        for pattern in _MORE_SENSITIVE_FOLDER_PATTERNS:
            if pattern.search(path_str):
                logger.debug("More Sensitive (folder pattern): %s", path_str)
                return DataSensitivityTier.MORE_SENSITIVE

        # 5. Check Sensitive — file extension
        if path.suffix.lower() in _SENSITIVE_EXTENSIONS:
            logger.debug("Sensitive (extension %s): %s", path.suffix, name)
            return DataSensitivityTier.SENSITIVE

        # 6. Check Sensitive — folder path patterns
        for pattern in _SENSITIVE_FOLDER_PATTERNS:
            if pattern.search(path_str):
                logger.debug("Sensitive (folder pattern): %s", path_str)
                return DataSensitivityTier.SENSITIVE

        # 7. Check Sensitive — filename patterns
        for pattern in _SENSITIVE_NAME_PATTERNS:
            if pattern.search(name):
                logger.debug("Sensitive (filename pattern): %s", name)
                return DataSensitivityTier.SENSITIVE

        # 8. Default: Liberal
        return DataSensitivityTier.LIBERAL

    def classify_text(self, content: str, context_hint: str = "") -> DataSensitivityTier:
        """
        Classify raw text content (e.g. from a message or pasted data).
        Used when no file path is available.
        """
        combined = (content + " " + context_hint).lower()

        # More Sensitive text signals
        more_sensitive_signals = [
            "aadhaar", "aadhar", "pan card", "passport number",
            "account number", "ifsc", "bank statement",
            "nda", "non-disclosure", "confidential agreement",
            "income tax return", "itr", "form 16",
        ]
        for signal in more_sensitive_signals:
            if signal in combined:
                return DataSensitivityTier.MORE_SENSITIVE

        # Sensitive text signals
        sensitive_signals = [
            "medical report", "prescription", "diagnosis",
            "personal diary", "private conversation",
            "my photos", "my pictures",
        ]
        for signal in sensitive_signals:
            if signal in combined:
                return DataSensitivityTier.SENSITIVE

        return DataSensitivityTier.LIBERAL

    def get_tier_label(self, tier: DataSensitivityTier) -> str:
        """Human-readable label for UI display."""
        labels = {
            DataSensitivityTier.LIBERAL: "General (Liberal)",
            DataSensitivityTier.SENSITIVE: "Personal (Sensitive)",
            DataSensitivityTier.MORE_SENSITIVE: "Private (More Sensitive)",
        }
        return labels[tier]

    def get_tier_description(self, tier: DataSensitivityTier) -> str:
        """Short description for user-facing display."""
        descriptions = {
            DataSensitivityTier.LIBERAL: "Standard access. No special protection.",
            DataSensitivityTier.SENSITIVE: "Personal data. Encrypted, network restricted, session PIN required.",
            DataSensitivityTier.MORE_SENSITIVE: "Critical private data. Strongest encryption, network blocked, PIN required.",
        }
        return descriptions[tier]


__all__ = ["DataClassifier"]
