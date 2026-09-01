"""Exception hierarchy for Xeren LLM models and providers."""

from typing import Any, Optional


class LLMError(Exception):
    """Base class for all LLM errors in Xeren."""

    def __init__(self, message: str, raw_error: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.raw_error = raw_error

    def __str__(self) -> str:
        if self.raw_error:
            return f"{self.message} (Raw details: {self.raw_error})"
        return self.message


class ModelNotFoundError(LLMError):
    """Raised when the specified model ID cannot be found by the provider or registry."""
    pass


class ProviderNotRegisteredError(LLMError):
    """Raised when an unknown or unregistered model provider is requested."""
    pass


class ProviderConnectionError(LLMError):
    """Raised when unable to connect to the model provider or local server."""
    pass


class AuthenticationError(LLMError):
    """Raised when API credentials, tokens, or permissions are rejected."""
    pass


class RateLimitError(LLMError):
    """Raised when the provider's rate limit or concurrency quota is exceeded."""
    pass


class ContextLengthExceededError(LLMError):
    """Raised when the prompt/context exceeds the model's maximum context window."""
    pass


class OutputParsingError(LLMError):
    """Raised when model output fails to parse into the requested structured schema."""

    def __init__(
        self,
        message: str,
        raw_output: Optional[str] = None,
        raw_error: Optional[Any] = None,
    ) -> None:
        super().__init__(message, raw_error=raw_error)
        self.raw_output = raw_output


class ConfigurationError(LLMError):
    """Raised when model configuration is invalid or missing required parameters."""
    pass


class InferenceTimeoutError(LLMError):
    """Raised when an inference call times out."""
    pass
