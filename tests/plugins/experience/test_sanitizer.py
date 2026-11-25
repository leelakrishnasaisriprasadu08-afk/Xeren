"""Tests for ExperienceSanitizerTool secret detection and redaction."""

import pytest

from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool


@pytest.fixture
def sanitizer():
    return ExperienceSanitizerTool()


def test_sanitizer_api_keys(sanitizer):
    """Verify API keys and access tokens are redacted from strings."""
    raw_text = (
        "Configure OpenAI client using sk-abcdef1234567890abcdef1234567890\n"
        "AWS credentials: AKIAIOSFODNN7EXAMPLE\n"
        "GitHub token: ghp_1234567890abcdef1234567890abcdef1234\n"
        "Auth header: Bearer ya29.a0ARrdaM-1234567890abcdef1234567890"
    )
    cleaned = sanitizer.sanitize_text(raw_text)
    assert "sk-" not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned
    assert "AKIA" not in cleaned
    assert "[REDACTED_AWS_KEY]" in cleaned
    assert "ghp_" not in cleaned
    assert "[REDACTED_GITHUB_TOKEN]" in cleaned
    assert "Bearer [REDACTED_TOKEN]" in cleaned


def test_sanitizer_passwords_and_private_keys(sanitizer):
    """Verify passwords and RSA private keys are redacted."""
    raw_text = (
        'database_connection: password="SuperSecretPassword123!"\n'
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y1234567890abcdef\n"
        "-----END RSA PRIVATE KEY-----"
    )
    cleaned = sanitizer.sanitize_text(raw_text)
    assert "SuperSecretPassword123!" not in cleaned
    assert "[REDACTED]" in cleaned
    assert "[REDACTED_PRIVATE_KEY]" in cleaned


def test_sanitizer_recursive_payload(sanitizer):
    """Verify recursive redaction across nested dictionaries and lists."""
    payload = {
        "user": "Alice",
        "keys": ["sk-1234567890abcdef1234567890", "harmless_data"],
        "nested": {
            "token": "Bearer abcdef1234567890abcdef1234567890",
            "count": 42,
        },
    }
    cleaned = sanitizer.sanitize_payload(payload)
    assert cleaned["user"] == "Alice"
    assert cleaned["keys"][0] == "[REDACTED_API_KEY]"
    assert cleaned["keys"][1] == "harmless_data"
    assert cleaned["nested"]["token"] == "Bearer [REDACTED_TOKEN]"
    assert cleaned["nested"]["count"] == 42
