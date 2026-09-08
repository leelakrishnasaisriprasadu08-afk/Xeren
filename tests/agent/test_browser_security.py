"""Tests for BrowserSecurityManager validating URLs, file boundaries, and secret redaction."""

from pathlib import Path
import tempfile
import pytest

from xeren.agent.browser.errors import BrowserSecurityError
from xeren.agent.browser.security import BrowserSecurityManager


@pytest.fixture
def security_setup():
    with tempfile.TemporaryDirectory(prefix="xeren_sec_") as tmpdir:
        ws = Path(tmpdir).resolve()
        upload_dir = ws / "uploads"
        download_dir = ws / "downloads"
        upload_dir.mkdir()
        download_dir.mkdir()

        sec = BrowserSecurityManager(
            allowed_workspace_dir=ws,
            allowed_upload_dir=upload_dir,
            allowed_download_dir=download_dir,
            allowed_domains=["example.com", "github.com"],
        )
        yield sec, ws, upload_dir, download_dir


def test_url_validation_schemes(security_setup):
    """Verify approved schemes pass and forbidden schemes are rejected."""
    sec, ws, _, _ = security_setup

    # Valid HTTPS and HTTP
    assert sec.validate_url("https://example.com") == "https://example.com"
    assert sec.validate_url("http://example.com/api") == "http://example.com/api"
    assert sec.validate_url("example.com/test") == "https://example.com/test"

    # Forbidden schemes
    with pytest.raises(BrowserSecurityError):
        sec.validate_url("javascript:alert('xss')")

    with pytest.raises(BrowserSecurityError):
        sec.validate_url("data:text/html,<b>exploit</b>")

    with pytest.raises(BrowserSecurityError):
        sec.validate_url("ftp://example.com/file")


def test_url_file_scheme_boundaries(security_setup):
    """Verify file:// scheme is strictly permitted only inside workspace."""
    sec, ws, _, _ = security_setup

    inside_file = ws / "index.html"
    inside_file.write_text("<h1>Safe</h1>", encoding="utf-8")

    # Valid file inside workspace
    valid_file_url = inside_file.as_uri()
    assert sec.validate_url(valid_file_url) == valid_file_url

    # Dangerous file outside workspace
    outside_file = ws.parent / "system_secret.txt"
    with pytest.raises(BrowserSecurityError):
        sec.validate_url(outside_file.as_uri())


def test_url_allowed_domains_filtering(security_setup):
    """Verify domain allowlist restricts external navigation."""
    sec, _, _, _ = security_setup

    assert sec.validate_url("https://example.com/subpage")
    assert sec.validate_url("https://sub.example.com")
    assert sec.validate_url("https://github.com/leela")

    # Unauthorized domain
    with pytest.raises(BrowserSecurityError) as exc_info:
        sec.validate_url("https://malicious-site.com")
    assert "not in allowed domains" in str(exc_info.value)


def test_upload_path_security(security_setup):
    """Verify upload paths are confined to allowed_upload_dir."""
    sec, ws, upload_dir, _ = security_setup

    valid_file = upload_dir / "valid_image.png"
    valid_file.write_text("fake_png", encoding="utf-8")
    assert sec.validate_upload_path(valid_file) == valid_file

    # Directory traversal
    traversal = upload_dir / ".." / "outside.txt"
    with pytest.raises(BrowserSecurityError):
        sec.validate_upload_path(traversal)

    # Non-existent file
    missing = upload_dir / "missing.txt"
    with pytest.raises(BrowserSecurityError):
        sec.validate_upload_path(missing)

    # Directory instead of file
    with pytest.raises(BrowserSecurityError):
        sec.validate_upload_path(upload_dir)


def test_download_path_security(security_setup):
    """Verify download paths and filenames cannot escape download_dir."""
    sec, ws, _, download_dir = security_setup

    # Valid save path
    dest = download_dir / "my_file.csv"
    assert sec.validate_download_path(dest) == dest

    # Filename with path traversal stripped
    sanitized_dest = sec.validate_download_path(filename="../../evil.exe")
    assert sanitized_dest == (download_dir / "evil.exe").resolve()

    # Destination escaping download dir
    bad_dir = ws.parent / "escape.csv"
    with pytest.raises(BrowserSecurityError):
        sec.validate_download_path(bad_dir)


def test_secret_redaction_patterns():
    """Verify secret credentials of diverse formats are masked."""
    raw_text = (
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret_payload\n"
        "AWS Access: AKIAIOSFODNN7EXAMPLE\n"
        "Google API: AIzaSyD-1234567890123456789012345678901\n"
        "OpenAI: sk-abcdefghijklmnopqrstuvwxyz1234567890\n"
        "GitHub: ghp_1234567890abcdefghijklmnopqrstuvwxyz\n"
        "Basic Auth: Basic dXNlcjpwYXNzd29yZA==\n"
        "password: 'MySecretPassword!'"
    )

    sanitized = BrowserSecurityManager.sanitize_text(raw_text)

    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
    assert "sk-abcdefghijklmnopqrstuvwxyz1234567890" not in sanitized
    assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in sanitized
    assert "AIzaSyD" not in sanitized
    assert "eyJhbGciOi" not in sanitized
    assert "dXNlcjpw" not in sanitized
    assert "MySecretPassword!" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_secret_redaction_in_dictionary():
    """Verify recursive dictionary key and value redaction."""
    data = {
        "username": "admin",
        "password": "ClearTextPassword123",
        "api_key": "sk-12345678901234567890",
        "headers": {
            "Authorization": "Bearer token1234567890",
            "Content-Type": "application/json",
        },
        "tags": ["public", "password: 'secret'"],
    }

    sanitized = BrowserSecurityManager.sanitize_dict(data)

    assert sanitized["username"] == "admin"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["headers"]["Authorization"] == "[REDACTED]"
    assert sanitized["headers"]["Content-Type"] == "application/json"
    assert "secret" not in str(sanitized["tags"])
