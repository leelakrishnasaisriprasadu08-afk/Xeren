"""Core schemas and data types for Xeren's 3-tier security system."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generator, List, Optional
import uuid

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sensitivity Tiers
# ---------------------------------------------------------------------------

class DataSensitivityTier(str, Enum):
    """The three data sensitivity blocks in Xeren."""

    LIBERAL = "liberal"
    """General files: code, notes, configs, public documents. No special protection."""

    SENSITIVE = "sensitive"
    """Personal files: photos, contacts, medical records, private messages.
    AES-256-CBC encrypted. Network access restricted. Session-auth required."""

    MORE_SENSITIVE = "more_sensitive"
    """Critical private data: Aadhaar, PAN, passports, bank statements, legal contracts.
    AES-256-GCM + PBKDF2 encrypted. Network BLOCKED. PIN required. Highest protection."""


# ---------------------------------------------------------------------------
# Auth Methods
# ---------------------------------------------------------------------------

class AuthMethod(str, Enum):
    """Available authentication mechanisms."""
    NONE = "none"
    PIN = "pin"
    BIOMETRIC = "biometric"
    SESSION_TOKEN = "session_token"


# ---------------------------------------------------------------------------
# Access Decision
# ---------------------------------------------------------------------------

class AccessOutcome(str, Enum):
    """Result of a security gate evaluation."""
    ALLOWED = "allowed"
    ALLOWED_FAST_PATH = "allowed_fast_path"   # Liberal — skipped upper layers
    DENIED = "denied"
    REQUIRES_AUTH = "requires_auth"
    REQUIRES_CLARIFICATION = "requires_clarification"


class AccessDecision(BaseModel):
    """Result returned by XerenSecurityGate for any data access request."""

    outcome: AccessOutcome
    tier: DataSensitivityTier
    reason: str = ""
    layers_passed: List[int] = Field(default_factory=list)
    unlock_challenge: Optional["UnlockChallenge"] = None

    @classmethod
    def allowed(cls, tier: DataSensitivityTier, layers: Optional[List[int]] = None) -> "AccessDecision":
        return cls(
            outcome=AccessOutcome.ALLOWED,
            tier=tier,
            reason="Access granted after all security checks.",
            layers_passed=layers or list(range(1, 9)),
        )

    @classmethod
    def fast_path(cls) -> "AccessDecision":
        return cls(
            outcome=AccessOutcome.ALLOWED_FAST_PATH,
            tier=DataSensitivityTier.LIBERAL,
            reason="Liberal tier — no security checks required.",
            layers_passed=[1, 2],
        )

    @classmethod
    def denied(cls, reason: str, tier: DataSensitivityTier = DataSensitivityTier.LIBERAL) -> "AccessDecision":
        return cls(outcome=AccessOutcome.DENIED, tier=tier, reason=reason)

    @classmethod
    def needs_auth(cls, challenge: "UnlockChallenge", tier: DataSensitivityTier) -> "AccessDecision":
        return cls(
            outcome=AccessOutcome.REQUIRES_AUTH,
            tier=tier,
            reason="Authentication required for this sensitivity tier.",
            unlock_challenge=challenge,
        )

    @property
    def is_allowed(self) -> bool:
        return self.outcome in (AccessOutcome.ALLOWED, AccessOutcome.ALLOWED_FAST_PATH)


# ---------------------------------------------------------------------------
# Unlock Challenge
# ---------------------------------------------------------------------------

class UnlockChallenge(BaseModel):
    """Sent to the user when tier authentication is required."""

    challenge_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tier: DataSensitivityTier
    method: AuthMethod
    prompt: str                # Human-readable prompt shown to user
    expires_at: datetime       # Challenge expires after this time
    context: str = ""          # Why this access is being requested

    @classmethod
    def pin_challenge(cls, tier: DataSensitivityTier, context: str = "") -> "UnlockChallenge":
        from datetime import timedelta
        prompt = (
            "Enter your 4-digit PIN to access this protected document."
            if tier == DataSensitivityTier.MORE_SENSITIVE
            else "Quick verification — enter your PIN to continue."
        )
        return cls(
            tier=tier,
            method=AuthMethod.PIN,
            prompt=prompt,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            context=context,
        )


# ---------------------------------------------------------------------------
# Audit Event
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    """A single immutable audit log entry for sensitive data access."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    path_hash: str                        # SHA-256 hash of path — never raw path
    tier: DataSensitivityTier
    operation: str                        # read, write, delete, scan
    outcome: AccessOutcome
    reason: str = ""
    layers_evaluated: List[int] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Encrypted Blob
# ---------------------------------------------------------------------------

class EncryptedBlob(BaseModel):
    """Encrypted data container with algorithm metadata."""

    algorithm: str               # "AES-256-CBC" or "AES-256-GCM"
    ciphertext: bytes
    iv: bytes                    # Initialization vector / nonce
    salt: bytes                  # PBKDF2 salt
    tag: Optional[bytes] = None  # GCM authentication tag (More Sensitive only)
    tier: DataSensitivityTier = DataSensitivityTier.SENSITIVE
    iterations: int = 100_000    # PBKDF2 iteration count

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "ciphertext": self.ciphertext.hex(),
            "iv": self.iv.hex(),
            "salt": self.salt.hex(),
            "tag": self.tag.hex() if self.tag else None,
            "tier": self.tier.value,
            "iterations": self.iterations,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EncryptedBlob":
        return cls(
            algorithm=d["algorithm"],
            ciphertext=bytes.fromhex(d["ciphertext"]),
            iv=bytes.fromhex(d["iv"]),
            salt=bytes.fromhex(d["salt"]),
            tag=bytes.fromhex(d["tag"]) if d.get("tag") else None,
            tier=DataSensitivityTier(d["tier"]),
            iterations=d.get("iterations", 100_000),
        )


# ---------------------------------------------------------------------------
# Credibility Score (for web search)
# ---------------------------------------------------------------------------

class DomainTier(str, Enum):
    """Trust tier for web source domains."""
    AUTHORITY = "authority"        # .gov, .edu, .who.int, arxiv.org
    TRUSTED_NEWS = "trusted_news"  # reuters.com, bbc.com, apnews.com
    COMMERCIAL = "commercial"      # General commercial sites
    UNKNOWN = "unknown"            # Unrecognized domains
    HARMFUL = "harmful"            # Flagged/blocked sources


class CredibilityScore(BaseModel):
    """Source credibility evaluation result for web search."""

    url: str
    domain_tier: DomainTier
    score: float = Field(ge=0.0, le=1.0)   # 0.0 = untrustworthy, 1.0 = highest trust
    is_harmful: bool = False
    flags: List[str] = Field(default_factory=list)  # ["single_source", "no_author", "spam_pattern"]
    recency_score: float = Field(default=0.5, ge=0.0, le=1.0)
    has_author: bool = False
    domain: str = ""


# ---------------------------------------------------------------------------
# Cross-Verification Report
# ---------------------------------------------------------------------------

class ClaimStatus(str, Enum):
    VERIFIED = "verified"         # 3+ sources agree
    UNVERIFIED = "unverified"     # Only 1 source
    CONTESTED = "contested"       # Sources disagree


class VerifiedClaim(BaseModel):
    """A factual claim with its verification status."""
    claim_text: str
    status: ClaimStatus
    supporting_sources: List[str] = Field(default_factory=list)
    contradicting_sources: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class VerificationReport(BaseModel):
    """Full cross-verification report for a research result."""
    verified_claims: List[VerifiedClaim] = Field(default_factory=list)
    unverified_claims: List[VerifiedClaim] = Field(default_factory=list)
    contested_claims: List[VerifiedClaim] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    sources_checked: int = 0
    cross_verification_summary: str = ""


__all__ = [
    "DataSensitivityTier",
    "AccessOutcome",
    "AccessDecision",
    "AuthMethod",
    "UnlockChallenge",
    "AuditEvent",
    "EncryptedBlob",
    "DomainTier",
    "CredibilityScore",
    "ClaimStatus",
    "VerifiedClaim",
    "VerificationReport",
]
