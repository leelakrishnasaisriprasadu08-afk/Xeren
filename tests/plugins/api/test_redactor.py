"""Secret redaction unit tests for ApiSecretRedactorTool."""

from xeren.plugins.api.tools.redactor import ApiSecretRedactorTool


def test_redactor_xeren_keys():
    """Verify Xeren live and test keys are masked."""
    redactor = ApiSecretRedactorTool()
    sample = "Key initialized: xrn_live_a1b2c3d4_8f9e0d1c2b3a4e5f6a7b8c9d0e1f2a3b in production."
    sanitized = redactor.sanitize_text(sample)
    assert "xrn_live_a1b2c3d4_8f9e0d1c2b3a4e5f6a7b8c9d0e1f2a3b" not in str(sanitized)
    assert "[REDACTED_XEREN_KEY]" in str(sanitized)

    sample_test = "Using test credentials: xrn_test_12345678_aabbccddeeff001122334455"
    assert "xrn_test_" not in str(redactor.sanitize_text(sample_test))


def test_redactor_external_keys():
    """Verify OpenAI, AWS, GitHub, and Bearer tokens are scrubbed."""
    redactor = ApiSecretRedactorTool()

    # OpenAI
    sk_sample = "Error calling provider: sk-1234567890abcdefghijklmnopqrstuv"
    assert "sk-1234567890" not in str(redactor.sanitize_text(sk_sample))

    # AWS
    aws_sample = "Access denied for AKIAIOSFODNN7EXAMPLE"
    assert "AKIAIOSFODNN7EXAMPLE" not in str(redactor.sanitize_text(aws_sample))

    # GitHub
    gh_sample = "Repo cloned with ghp_123456789012345678901234567890123456"
    assert "ghp_123456" not in str(redactor.sanitize_text(gh_sample))

    # Bearer token
    bearer_sample = "Authorization: Bearer mySecretToken1234567890abcdef"
    assert "mySecretToken1234567890abcdef" not in str(redactor.sanitize_text(bearer_sample))


def test_redactor_internal_filesystem_paths():
    """Verify Windows and Unix absolute system paths are redacted."""
    redactor = ApiSecretRedactorTool()

    # Windows user path
    win_path = "Log written to C:\\Users\\Administrator\\AppData\\Local\\secret.log"
    assert "Administrator" not in str(redactor.sanitize_text(win_path))
    assert "[REDACTED_PATH]" in str(redactor.sanitize_text(win_path))

    # Unix root path
    unix_path = "Config read from /etc/shadow or /home/ubuntu/.env"
    assert "/etc/shadow" not in str(redactor.sanitize_text(unix_path))
    assert "[REDACTED_PATH]" in str(redactor.sanitize_text(unix_path))


def test_redactor_sanitize_headers():
    """Verify sensitive HTTP headers are masked."""
    redactor = ApiSecretRedactorTool()
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer xrn_live_secret12345",
        "X-API-Key": "xrn_test_key_999",
        "Cookie": "session_id=abcdef",
    }

    clean = redactor.sanitize_headers(headers)
    assert clean["Content-Type"] == "application/json"
    assert clean["Authorization"] == "Bearer [REDACTED]"
    assert clean["X-API-Key"] == "[REDACTED]"
    assert clean["Cookie"] == "[REDACTED]"
    assert "xrn_live_secret12345" not in str(clean)


def test_redactor_sanitize_payload_nested():
    """Verify recursive payload dictionary and list scrubbing."""
    redactor = ApiSecretRedactorTool()
    payload = {
        "client": "web",
        "api_key": "xrn_live_topsecret1234567890abcdef",
        "nested": {
            "error_path": "C:\\Users\\manid\\secret.py",
            "tokens": ["ghp_111122223333444455556666777788889999"],
        },
    }
    clean = redactor.sanitize_payload(payload)
    assert clean["api_key"] == "[REDACTED]"
    assert clean["nested"]["error_path"] == "[REDACTED_PATH]"
    assert "ghp_111122223333444455556666777788889999" not in str(clean)
