"""Configuration and domain exceptions for live search providers."""

from enum import Enum
import os
import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from xeren.plugins.errors import PluginError


class SearchProvider(str, Enum):
    """Supported search providers."""

    MOCK = "mock"
    TAVILY = "tavily"
    BRAVE = "brave"
    SEARXNG = "searxng"
    GENERIC = "generic"


class SearchProviderError(PluginError):
    """Base exception for external search provider errors."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        raw_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, plugin_name="research", raw_error=raw_error)
        self.provider = provider
        self.status_code = status_code

    def __str__(self) -> str:
        prov = f"[{self.provider}] " if self.provider else ""
        code = f"(HTTP {self.status_code}) " if self.status_code else ""
        return f"{prov}{code}{self.message}"


class SearchAuthError(SearchProviderError):
    """Authentication or authorization failure with search provider."""
    pass


class SearchRateLimitError(SearchProviderError):
    """Rate limit exceeded (HTTP 429) on search provider."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after: Optional[float] = None,
        raw_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, provider=provider, status_code=429, raw_error=raw_error)
        self.retry_after = retry_after


class SearchTimeoutError(SearchProviderError):
    """Search request timed out."""
    pass


def mask_api_key(key: Optional[str]) -> str:
    """Safely mask API key for logging and diagnostic output."""
    if not key:
        return "(none)"
    clean = key.strip()
    if len(clean) <= 8:
        return "***"
    return f"{clean[:4]}...{clean[-4:]}"


def sanitize_message(message: str, api_key: Optional[str]) -> str:
    """Scrub sensitive API key occurrences from error strings and log messages."""
    if not api_key or len(api_key.strip()) < 4:
        return message
    return message.replace(api_key.strip(), mask_api_key(api_key))


class SearchConfig(BaseModel):
    """Configuration for search providers."""

    provider: str = Field(default=SearchProvider.MOCK.value, description="Provider identifier")
    api_key: Optional[str] = Field(default=None, repr=False, description="Provider API key (masked in repr)")
    base_url: Optional[str] = Field(default=None, description="Custom base URL for search API")
    timeout_seconds: float = Field(default=10.0, gt=0.0, description="Network request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts on transient failures")
    backoff_factor: float = Field(default=0.5, ge=0.0, description="Base exponential backoff factor")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional custom HTTP headers")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")

    @classmethod
    def from_env(cls, provider: Optional[str] = None) -> "SearchConfig":
        """Load search configuration from environment variables."""
        env_provider = provider or os.getenv("XEREN_SEARCH_PROVIDER", "").strip().lower()

        # Check provider-specific keys
        tavily_key = os.getenv("TAVILY_API_KEY") or os.getenv("XEREN_TAVILY_API_KEY")
        brave_key = os.getenv("BRAVE_API_KEY") or os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("XEREN_BRAVE_API_KEY")
        searxng_url = os.getenv("SEARXNG_URL") or os.getenv("XEREN_SEARXNG_URL")
        generic_key = os.getenv("XEREN_SEARCH_API_KEY")

        # Auto-detect provider if not explicitly configured
        if not env_provider:
            if tavily_key:
                env_provider = SearchProvider.TAVILY.value
            elif brave_key:
                env_provider = SearchProvider.BRAVE.value
            elif searxng_url:
                env_provider = SearchProvider.SEARXNG.value
            else:
                env_provider = SearchProvider.MOCK.value

        api_key = None
        base_url = None

        if env_provider == SearchProvider.TAVILY.value:
            api_key = tavily_key or generic_key
            base_url = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com")
        elif env_provider == SearchProvider.BRAVE.value:
            api_key = brave_key or generic_key
            base_url = os.getenv("BRAVE_BASE_URL", "https://api.search.brave.com")
        elif env_provider == SearchProvider.SEARXNG.value:
            base_url = searxng_url or "http://localhost:8080"
            api_key = generic_key
        elif env_provider == SearchProvider.GENERIC.value:
            api_key = generic_key
            base_url = os.getenv("XEREN_SEARCH_BASE_URL")

        timeout_str = os.getenv("XEREN_SEARCH_TIMEOUT_SECONDS", "10.0")
        try:
            timeout_val = float(timeout_str)
        except ValueError:
            timeout_val = 10.0

        retries_str = os.getenv("XEREN_SEARCH_MAX_RETRIES", "3")
        try:
            retries_val = int(retries_str)
        except ValueError:
            retries_val = 3

        backoff_str = os.getenv("XEREN_SEARCH_BACKOFF_FACTOR", "0.5")
        try:
            backoff_val = float(backoff_str)
        except ValueError:
            backoff_val = 0.5

        return cls(
            provider=env_provider,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_val,
            max_retries=retries_val,
            backoff_factor=backoff_val,
        )


__all__ = [
    "SearchProvider",
    "SearchConfig",
    "SearchProviderError",
    "SearchAuthError",
    "SearchRateLimitError",
    "SearchTimeoutError",
    "mask_api_key",
    "sanitize_message",
]
