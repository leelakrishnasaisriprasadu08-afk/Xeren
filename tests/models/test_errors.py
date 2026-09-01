"""Unit tests for the LLM error hierarchy."""

import pytest

from xeren.models.errors import (
    AuthenticationError,
    ConfigurationError,
    ContextLengthExceededError,
    InferenceTimeoutError,
    LLMError,
    ModelNotFoundError,
    OutputParsingError,
    ProviderConnectionError,
    ProviderNotRegisteredError,
    RateLimitError,
)


def test_error_inheritance() -> None:
    errors = [
        ModelNotFoundError("Model not found"),
        ProviderNotRegisteredError("Provider missing"),
        ProviderConnectionError("Connection refused"),
        AuthenticationError("Invalid API key"),
        RateLimitError("Quota exceeded"),
        ContextLengthExceededError("Context too long"),
        OutputParsingError("JSON invalid"),
        ConfigurationError("Config invalid"),
        InferenceTimeoutError("Timeout after 60s"),
    ]
    for err in errors:
        assert isinstance(err, LLMError)
        assert isinstance(err, Exception)


def test_error_str_formatting() -> None:
    err_simple = LLMError("Something went wrong")
    assert str(err_simple) == "Something went wrong"

    err_detailed = LLMError("Failed request", raw_error={"code": 500})
    assert "Failed request" in str(err_detailed)
    assert "{'code': 500}" in str(err_detailed)


def test_output_parsing_error_attributes() -> None:
    err = OutputParsingError("Schema mismatch", raw_output='{"invalid": true}')
    assert err.raw_output == '{"invalid": true}'
    assert "Schema mismatch" in str(err)
