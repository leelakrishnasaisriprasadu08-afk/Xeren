"""Network isolation guard — blocks sensitive data from leaving the device."""

from __future__ import annotations

import logging
import socket
from typing import Optional

from xeren.security.schemas import DataSensitivityTier

logger = logging.getLogger("xeren.security.network_guard")


class NetworkGuard:
    """
    Enforces network access restrictions per data sensitivity tier.

    LIBERAL:          Network allowed for all operations.
    SENSITIVE:        Network allowed, but actual content is stripped from
                      outbound requests (metadata only, no file content).
    MORE_SENSITIVE:   Network HARD BLOCKED — data never leaves the device.
                      This is enforced at the policy level.
    """

    def __init__(self) -> None:
        self._online: Optional[bool] = None
        self._offline_probe_host = "8.8.8.8"
        self._offline_probe_port = 53
        self._offline_probe_timeout = 2.0

    # ------------------------------------------------------------------
    # Connectivity Check
    # ------------------------------------------------------------------

    def is_online(self, force_check: bool = False) -> bool:
        """
        Check if the device has internet connectivity.
        Caches result briefly — pass force_check=True to re-probe.
        """
        if self._online is not None and not force_check:
            return self._online

        try:
            socket.setdefaulttimeout(self._offline_probe_timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                (self._offline_probe_host, self._offline_probe_port)
            )
            self._online = True
        except (socket.error, OSError):
            self._online = False

        return self._online

    def is_offline(self) -> bool:
        return not self.is_online()

    def clear_connectivity_cache(self) -> None:
        """Force re-check on next call."""
        self._online = None

    # ------------------------------------------------------------------
    # Network Permission Checks
    # ------------------------------------------------------------------

    def can_send_to_network(self, tier: DataSensitivityTier) -> bool:
        """
        Return True if data of this tier is allowed to reach the network.

        LIBERAL:          True (always allowed)
        SENSITIVE:        True, but caller must strip content first
        MORE_SENSITIVE:   False — ALWAYS blocked
        """
        if tier == DataSensitivityTier.MORE_SENSITIVE:
            return False
        return True

    def can_use_llm_api(self, tier: DataSensitivityTier) -> bool:
        """
        Whether data of this tier may be sent to ANY LLM endpoint.
        Since Xeren uses local LLMs, this is about the content in the prompt.

        MORE_SENSITIVE: Never in LLM context window.
        SENSITIVE: Allowed in local LLM (no network), blocked for remote APIs.
        LIBERAL: Always allowed.
        """
        if tier == DataSensitivityTier.MORE_SENSITIVE:
            return False
        return True  # Local LLM is fine for all other tiers

    def validate_operation(
        self,
        tier: DataSensitivityTier,
        operation: str,
    ) -> tuple[bool, str]:
        """
        Validate whether an operation is allowed for a given tier.

        Returns: (is_allowed, reason_if_denied)
        """
        network_ops = {"network", "api_call", "web_search", "upload", "email", "webhook"}
        llm_ops = {"llm_prompt", "llm_generate", "embed"}

        if operation in network_ops:
            if not self.can_send_to_network(tier):
                return False, (
                    f"Network operation '{operation}' is blocked for '{tier.value}' data. "
                    "More Sensitive data never leaves your device."
                )

        if operation in llm_ops:
            if not self.can_use_llm_api(tier):
                return False, (
                    f"LLM operation '{operation}' is blocked for '{tier.value}' data. "
                    "This content is never included in AI prompts."
                )

        return True, ""

    # ------------------------------------------------------------------
    # Offline Capability Check
    # ------------------------------------------------------------------

    def get_offline_capabilities(self) -> dict[str, bool]:
        """
        What Xeren can do when offline.
        Used to provide graceful degradation messages.
        """
        return {
            "local_llm": True,           # Local LLM always works
            "file_access": True,         # File system always works
            "rag_retrieval": True,       # Local RAG works
            "web_search": False,         # SearXNG needs network
            "account_sync": False,       # Fiverr / platform connectors need network
            "oauth_refresh": False,      # Token refresh needs network
            "liberal_data": True,
            "sensitive_data": True,      # SAFER offline — truly local
            "more_sensitive_data": True, # SAFEST offline
        }

    def get_offline_message(self, feature: str) -> str:
        """Return a friendly offline degradation message for a specific feature."""
        messages = {
            "web_search": (
                "I'm currently offline — can't search the web right now. "
                "I can help you with your local files and knowledge base."
            ),
            "account_sync": (
                "Can't reach your account right now — working offline. "
                "I'll sync when you're back online."
            ),
            "oauth_refresh": (
                "Can't refresh authentication — working with cached access."
            ),
        }
        return messages.get(
            feature,
            "This feature requires internet access. I'll try again when you're online.",
        )


__all__ = ["NetworkGuard"]
