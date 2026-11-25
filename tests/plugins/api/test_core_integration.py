"""Integration tests for XerenCore with API Plugin and full 10-plugin coexistence."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.api.plugin import ApiPlugin
from xeren.plugins.api.schemas import ApiRequest


def test_core_coexistence_all_ten_plugins():
    """Verify XerenCore boots cleanly with all 10 standard plugins registered and operational."""
    core = XerenCore()
    plugin_names = [p.name for p in core.list_plugins()]

    expected_plugins = [
        "research",
        "knowledge",
        "coding",
        "website",
        "data",
        "file",
        "verification",
        "experience",
        "automation",
        "api",
    ]
    for expected in expected_plugins:
        assert expected in plugin_names, f"Missing expected plugin: {expected}"

    assert len(plugin_names) >= 10
    assert core.has_plugin("api")

    api_p = core.get_plugin("api")
    assert isinstance(api_p, ApiPlugin)

    # Verify overall 10-plugin health report
    health_report = core.check_health()
    assert health_report["healthy"] is True
    assert "api" in health_report["plugins"]
    assert health_report["plugins"]["api"]["status"] == "healthy"
    assert len(health_report["plugins"]) >= 10


def test_core_api_key_lifecycle_convenience_methods():
    """Verify core.create_api_key, core.validate_api_key, core.rotate_api_key, core.revoke_api_key."""
    core = XerenCore()

    # 1. Create API key
    created = core.create_api_key(
        name="Integration Test Key",
        scopes=["research", "data"],
        rate_limit_per_minute=100,
    )
    assert created.raw_key.startswith("xrn_live_")
    key_id = created.key_id

    # 2. Validate API key
    val_res = core.validate_api_key(created.raw_key)
    assert val_res.success is True
    assert val_res.is_authenticated is True
    assert val_res.key_metadata is not None
    assert val_res.key_metadata.key_id == key_id

    # 3. Rotate API key
    rot_res = core.rotate_api_key(key_id, grace_period_seconds=0.0)
    assert rot_res.success is True
    assert rot_res.created_key is not None
    assert rot_res.created_key.key_id != key_id

    # 4. Revoke the new key
    rev_res = core.revoke_api_key(rot_res.created_key.key_id, reason="Testing revocation")
    assert rev_res.success is True


def test_core_handle_api_request_pipeline():
    """Verify end-to-end request handling through XerenCore gateway dispatch."""
    core = XerenCore()

    # Create key with data scope
    key_resp = core.create_api_key(name="Data Worker", scopes=["data"])

    # Make request to /v1/data
    req = ApiRequest(
        endpoint="/v1/data",
        method="POST",
        body={"data": "Name,Age\nAlice,30\nBob,25", "operation": "inspect"},
        api_key=key_resp.raw_key,
    )

    api_resp = core.handle_api_request(req)
    assert api_resp.success is True
    assert api_resp.status_code == 200
    assert api_resp.data is not None


def test_core_api_error_redaction():
    """Verify that errors dispatched through the API do not expose internal paths or raw traces."""
    core = XerenCore()
    api_p = core.get_plugin("api")
    assert isinstance(api_p, ApiPlugin)

    # Inject mock dispatcher that raises an exception with sensitive internal path and token
    def failing_dispatcher(plugin: str, payload: dict):
        raise RuntimeError(
            "Crash at C:\\Users\\manid\\secret_module.py: Access denied using sk-abcdef1234567890abcdef12345"
        )

    api_p.registry.set_custom_dispatcher(failing_dispatcher)

    # Key with research scope
    key_resp = core.create_api_key(name="Research Error Tester", scopes=["research"])

    req = ApiRequest(
        endpoint="/v1/research",
        method="POST",
        body={"query": "test"},
        api_key=key_resp.raw_key,
    )

    api_resp = core.handle_api_request(req)
    assert api_resp.success is False
    assert api_resp.status_code == 500
    assert api_resp.error is not None

    # Verify message has been scrubbed
    err_msg = api_resp.error.message
    assert "C:\\Users\\manid" not in err_msg
    assert "sk-abcdef123456" not in err_msg
    assert "[REDACTED_PATH]" in err_msg
    assert "[REDACTED_API_KEY]" in err_msg
