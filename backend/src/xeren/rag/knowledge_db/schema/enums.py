"""Enumerations for Xeren Sovereign Knowledge DB subsystem."""

from enum import Enum


class KnowledgeLifecycleState(str, Enum):
    """Lifecycle states for knowledge objects preserving historical evolution."""

    INGESTED = "INGESTED"                  # Raw source accepted into storage
    PROCESSED = "PROCESSED"                # Cleaned, normalized, and chunked
    INDEXED = "INDEXED"                    # Vector & lexical indices computed
    VALIDATED = "VALIDATED"                # Integrity & schema constraints verified
    ACTIVE = "ACTIVE"                      # Live in active knowledge retrieval pool
    UPDATED = "UPDATED"                    # Newer minor version or clarification registered
    QUALIFIED = "QUALIFIED"                # Qualified by caveats or partial evidence
    CONTRADICTED = "CONTRADICTED"          # Actively challenged by conflicting claims
    SUPERSEDED = "SUPERSEDED"              # Formally replaced by a newer authoritative document
    ARCHIVED = "ARCHIVED"                  # Retired from default retrieval; preserved for audit


class KnowledgeRelationshipType(str, Enum):
    """Knowledge graph semantic edge types between chunks."""

    SUPPORTS = "SUPPORTS"                  # Provides evidentiary support
    CONTRADICTS = "CONTRADICTS"            # Conflicts with or refutes target chunk
    EXPANDS = "EXPANDS"                    # Elaborates or provides additional detail
    REFERENCES = "REFERENCES"              # Cites or mentions target chunk
    SUPERSEDES = "SUPERSEDES"              # Explicitly replaces target chunk
    QUALIFIES = "QUALIFIES"                # Places restrictions/conditions on target chunk
    UPDATES = "UPDATES"                    # Incremental modification of target chunk
    DUPLICATES = "DUPLICATES"              # Exact or near-exact semantic duplicate


class ClaimType(str, Enum):
    """Epistemic classification of extracted or user assertions."""

    FACT = "FACT"                          # Directly verifiable factual statement
    INFERENCE = "INFERENCE"                # Derived deduction from multiple evidence pieces
    HYPOTHESIS = "HYPOTHESIS"              # Unverified proposition pending empirical test
    RULE = "RULE"                          # Prescriptive policy, constraint, or invariant


class TelemetryPrivacyPolicy(str, Enum):
    """Controls privacy retention for retrieval event queries."""

    FULL = "FULL"                          # Stores query text and SHA-256 hash (internal debugging)
    MINIMIZED = "MINIMIZED"                # Stores truncated/sanitized query text and hash
    HASH_ONLY = "HASH_ONLY"                # Stores strictly SHA-256 hash of query; zero raw text


class HealthState(str, Enum):
    """Operational health indicators for Primary and Backup databases."""

    PRIMARY_HEALTHY = "PRIMARY_HEALTHY"    # Primary operational, integrity checks pass
    PRIMARY_DEGRADED = "PRIMARY_DEGRADED"  # Operational but pending backup or index synchronization
    PRIMARY_CORRUPTED = "PRIMARY_CORRUPTED"# File I/O fault, SQLite corruption, or missing indexes
    BACKUP_AVAILABLE = "BACKUP_AVAILABLE"  # Verified passive backup snapshot available
    BACKUP_INVALID = "BACKUP_INVALID"      # Backup corrupted, missing, or checksum mismatch
