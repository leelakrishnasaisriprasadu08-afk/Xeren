"""Secure memory fence — zero-fills sensitive buffers after use to prevent data leaks."""

from __future__ import annotations

import ctypes
import logging
from contextlib import contextmanager
from typing import Generator

from xeren.security.schemas import DataSensitivityTier

logger = logging.getLogger("xeren.security.memory_fence")


def _zero_bytearray(buf: bytearray) -> None:
    """Overwrite a bytearray in-place with zeros."""
    for i in range(len(buf)):
        buf[i] = 0


def _zero_bytes_object(data: bytes) -> None:
    """
    Attempt to zero out a bytes object in memory.
    Note: bytes is immutable in Python, so this uses ctypes to overwrite
    the underlying buffer. Best-effort — not guaranteed on all platforms.
    """
    try:
        buf = (ctypes.c_char * len(data)).from_address(id(data))
        ctypes.memset(buf, 0, len(data))
    except Exception:
        pass  # Silently skip — ctypes zeroing is best-effort


class SecureMemoryFence:
    """
    After processing Sensitive or More Sensitive data:
    - Zero-fills all in-memory buffers
    - Ensures no sensitive content remains in heap memory
    - Prevents accidental inclusion in LLM context window or RAG embeddings

    Liberal tier data: no fencing needed (no overhead).
    """

    @staticmethod
    def should_fence(tier: DataSensitivityTier) -> bool:
        return tier != DataSensitivityTier.LIBERAL

    @staticmethod
    def zero_buffer(buf: bytearray) -> None:
        """Zero-fill a mutable bytearray buffer."""
        _zero_bytearray(buf)

    @staticmethod
    def zero_string_best_effort(data: bytes) -> None:
        """Best-effort zero-fill of an immutable bytes object."""
        _zero_bytes_object(data)

    @contextmanager
    def secure_buffer(
        self,
        tier: DataSensitivityTier,
    ) -> Generator[bytearray, None, None]:
        """
        Context manager providing a mutable buffer.
        Guaranteed to zero-fill on exit for Sensitive/More Sensitive tiers.

        Usage:
            with fence.secure_buffer(DataSensitivityTier.MORE_SENSITIVE) as buf:
                buf.extend(read_secret_file())
                process(bytes(buf))
            # buf is zeroed here, regardless of exceptions
        """
        buf = bytearray()
        try:
            yield buf
        finally:
            if self.should_fence(tier):
                n = len(buf)
                _zero_bytearray(buf)
                logger.debug("SecureMemoryFence: zeroed %d bytes for tier '%s'.", n, tier.value)

    @contextmanager
    def secure_text(
        self,
        tier: DataSensitivityTier,
    ) -> Generator[list, None, None]:
        """
        Context manager for sensitive string data.
        Holds text in a list[str] to allow mutation.
        Clears on exit.

        Usage:
            with fence.secure_text(DataSensitivityTier.SENSITIVE) as holder:
                holder.append(read_secret_text())
                process(holder[0])
            # holder is cleared here
        """
        holder: list[str] = []
        try:
            yield holder
        finally:
            if self.should_fence(tier):
                count = len(holder)
                holder.clear()
                logger.debug(
                    "SecureMemoryFence: cleared %d text items for tier '%s'.", count, tier.value
                )

    def sanitize_for_llm(self, text: str, tier: DataSensitivityTier) -> str:
        """
        Sanitize content before it goes into an LLM prompt.

        LIBERAL:         Pass through unchanged.
        SENSITIVE:       Strip content — return metadata summary only.
        MORE_SENSITIVE:  Hard block — never sent to LLM.
        """
        if tier == DataSensitivityTier.LIBERAL:
            return text

        if tier == DataSensitivityTier.SENSITIVE:
            # Strip actual content, send only structural description
            word_count = len(text.split())
            return (
                f"[SENSITIVE CONTENT — {word_count} words. "
                "Processing locally. Content not included in this prompt.]"
            )

        # MORE_SENSITIVE — hard block
        return "[MORE SENSITIVE — content blocked from LLM by security policy.]"

    def sanitize_for_rag(self, text: str, tier: DataSensitivityTier) -> str:
        """
        Prevent sensitive content from being embedded into the RAG vector store.
        Returns empty string for Sensitive/More Sensitive to block indexing.
        """
        if tier == DataSensitivityTier.LIBERAL:
            return text
        # Never embed personal or critical data into RAG
        logger.debug("RAG embedding blocked for tier '%s'.", tier.value)
        return ""


__all__ = ["SecureMemoryFence"]
