"""End-to-end request handling, authorization, and ASGI tests for ApiGatewayTool."""

import json
import pytest

from xeren.plugins.api.schemas import ApiRequest
from xeren.plugins.api.tools.auth import ApiKeyManagerTool
from xeren.plugins.api.tools.gateway import ApiGatewayTool
from xeren.plugins.api.tools.limiter import SlidingWindowRateLimiter
from xeren.plugins.api.tools.redactor import ApiSecretRedactorTool
from xeren.plugins.api.tools.store import InMemoryApiKeyStore
from xeren.plugins.api.tools.validator import RequestValidatorTool


def test_gateway_public_health_endpoint():
    """Verify /v1/health is accessible without API key credentials."""
    gateway = ApiGatewayTool()
    req = ApiRequest(endpoint="/v1/health", method="GET")

    res = gateway.handle_request(req)
    assert res.success is True
    assert res.status_code == 200
    assert isinstance(res.data, dict)
    assert res.data["status"] == "healthy"
    assert res.data["version"] == "v1"


def test_gateway_missing_and_invalid_api_key():
    """Verify 401 Unauthorized for missing or invalid API keys."""
    gateway = ApiGatewayTool()

    # Missing API key
    req_missing = ApiRequest(endpoint="/v1/research", method="POST", body={"query": "test"})
    res1 = gateway.handle_request(req_missing)
    assert res1.success is False
    assert res1.status_code == 401
    assert res1.error is not None
    assert res1.error.code == "UNAUTHORIZED"

    # Invalid API key
    req_invalid = ApiRequest(
        endpoint="/v1/research",
        method="POST",
        headers={"Authorization": "Bearer xrn_live_invalid_key_value_123456"},
    )
    res2 = gateway.handle_request(req_invalid)
    assert res2.success is False
    assert res2.status_code == 401


def test_gateway_scoped_authorization():
    """Verify 403 Forbidden when key lacks necessary route scope."""
    store = InMemoryApiKeyStore()
    auth = ApiKeyManagerTool(store=store)
    gateway = ApiGatewayTool(auth_manager=auth)

    # Key with ONLY 'research' scope
    _, research_key = auth.generate_key(name="Research Client", scopes=["research"])

    # 1. Accessing /v1/research succeeds
    req_allowed = ApiRequest(
        endpoint="/v1/research",
        method="POST",
        body={"query": "AI systems"},
        api_key=research_key,
    )
    res_allowed = gateway.handle_request(req_allowed)
    assert res_allowed.success is True
    assert res_allowed.status_code == 200

    # 2. Accessing /v1/coding fails with 403 Forbidden
    req_forbidden = ApiRequest(
        endpoint="/v1/coding",
        method="POST",
        body={"task": "write python"},
        api_key=research_key,
    )
    res_forbidden = gateway.handle_request(req_forbidden)
    assert res_forbidden.success is False
    assert res_forbidden.status_code == 403
    assert res_forbidden.error is not None
    assert res_forbidden.error.code == "FORBIDDEN"


def test_gateway_rate_limiting():
    """Verify 429 Rate Limited when key exhausts permitted request frequency."""
    store = InMemoryApiKeyStore()
    auth = ApiKeyManagerTool(store=store)
    limiter = SlidingWindowRateLimiter()
    gateway = ApiGatewayTool(auth_manager=auth, rate_limiter=limiter)

    # Key with 2 requests per minute
    _, key = auth.generate_key(name="Restricted Client", scopes=["*"], rate_limit_per_minute=2)

    req = ApiRequest(endpoint="/v1/research", method="POST", api_key=key)

    # First 2 requests succeed
    res1 = gateway.handle_request(req)
    assert res1.status_code == 200

    res2 = gateway.handle_request(req)
    assert res2.status_code == 200

    # 3rd request rejected with 429
    res3 = gateway.handle_request(req)
    assert res3.status_code == 429
    assert res3.success is False
    assert res3.error is not None
    assert res3.error.code == "RATE_LIMITED"
    assert "X-RateLimit-Limit" in res3.metadata


def test_gateway_key_management_endpoints():
    """Verify creating, listing, rotating, and revoking keys via gateway."""
    store = InMemoryApiKeyStore()
    auth = ApiKeyManagerTool(store=store)
    gateway = ApiGatewayTool(auth_manager=auth)

    # Provision admin key
    _, admin_key = auth.generate_key(name="Root Admin", scopes=["admin"])

    # 1. Create key via POST /v1/keys
    create_req = ApiRequest(
        endpoint="/v1/keys",
        method="POST",
        body={"name": "Sub Client", "scopes": ["data", "file"], "rate_limit_per_minute": 100},
        api_key=admin_key,
    )
    create_res = gateway.handle_request(create_req)
    assert create_res.status_code == 201
    assert isinstance(create_res.data, dict)
    assert "raw_key" in create_res.data
    sub_key_id = str(create_res.data["key_id"])

    # 2. List keys via GET /v1/keys
    list_req = ApiRequest(endpoint="/v1/keys", method="GET", api_key=admin_key)
    list_res = gateway.handle_request(list_req)
    assert list_res.status_code == 200
    assert isinstance(list_res.data, list)
    assert len(list_res.data) >= 2

    # 3. Rotate key via POST /v1/keys/rotate
    rotate_req = ApiRequest(
        endpoint="/v1/keys/rotate",
        method="POST",
        body={"key_id": sub_key_id, "grace_period_seconds": 0.0},
        api_key=admin_key,
    )
    rotate_res = gateway.handle_request(rotate_req)
    assert rotate_res.status_code == 200
    assert isinstance(rotate_res.data, dict)
    assert rotate_res.data["key_id"] != sub_key_id

    # 4. Revoke key via POST /v1/keys/revoke
    revoke_req = ApiRequest(
        endpoint="/v1/keys/revoke",
        method="POST",
        body={"key_id": sub_key_id, "reason": "Revoked in test"},
        api_key=admin_key,
    )
    revoke_res = gateway.handle_request(revoke_req)
    assert revoke_res.status_code == 200
    assert isinstance(revoke_res.data, dict)
    assert revoke_res.data["revoked"] is True


def test_gateway_audit_logging_no_secrets():
    """Verify request events are logged without recording raw API keys."""
    store = InMemoryApiKeyStore()
    auth = ApiKeyManagerTool(store=store)
    gateway = ApiGatewayTool(auth_manager=auth)

    _, key = auth.generate_key(name="Audited Client")
    req = ApiRequest(
        endpoint="/v1/research",
        method="POST",
        api_key=key,
        headers={"Authorization": f"Bearer {key}"},
    )
    gateway.handle_request(req)

    logs = gateway.get_audit_logs(limit=10)
    assert len(logs) >= 2

    # Verify no raw key leaked into audit trail
    log_dump = json.dumps(logs)
    assert key not in log_dump
    assert "[REDACTED]" in log_dump


@pytest.mark.asyncio
async def test_gateway_asgi_app_callable():
    """Verify ASGI 3.0 interface parses request, dispatches, and yields HTTP response."""
    gateway = ApiGatewayTool()

    # Scope for GET /v1/health
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/health",
        "headers": [(b"host", b"localhost")],
        "client": ("127.0.0.1", 12345),
    }

    sent_messages = []

    async def mock_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def mock_send(message):
        sent_messages.append(message)

    await gateway(scope, mock_receive, mock_send)

    assert len(sent_messages) == 2
    # First message: response start
    assert sent_messages[0]["type"] == "http.response.start"
    assert sent_messages[0]["status"] == 200

    # Second message: response body
    assert sent_messages[1]["type"] == "http.response.body"
    body_data = json.loads(sent_messages[1]["body"].decode("utf-8"))
    assert body_data["success"] is True
    assert body_data["data"]["status"] == "healthy"
