"""Unit tests for API plugin schemas, serialization, and validation."""

from datetime import datetime, timedelta, timezone

from xeren.plugins.api.schemas import (
    ApiError,
    ApiHealthReport,
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyEnvironment,
    ApiKeyMetadata,
    ApiOperation,
    ApiRequest,
    ApiResponse,
    ApiResult,
    ApiScope,
)


def test_api_enums():
    """Verify operations and scopes enum values."""
    assert ApiOperation.API_REQUEST == "api_request"
    assert ApiOperation.API_RESPONSE == "api_response"
    assert ApiOperation.API_KEY_AUTHENTICATION == "api_key_authentication"
    assert ApiOperation.API_KEY_ROTATION == "api_key_rotation"
    assert ApiOperation.API_KEY_REVOCATION == "api_key_revocation"
    assert ApiOperation.SCOPED_PERMISSIONS == "scoped_permissions"
    assert ApiOperation.REQUEST_VALIDATION == "request_validation"
    assert ApiOperation.RATE_LIMITING == "rate_limiting"
    assert ApiOperation.REQUEST_LOGGING == "request_logging"
    assert ApiOperation.HEALTH_STATUS == "health_status"

    assert ApiScope.ALL == "*"
    assert ApiScope.ADMIN == "admin"
    assert ApiScope.RESEARCH == "research"
    assert ApiScope.KNOWLEDGE == "knowledge"
    assert ApiScope.CODING == "coding"
    assert ApiScope.WEBSITE == "website"
    assert ApiScope.DATA == "data"
    assert ApiScope.FILE == "file"
    assert ApiScope.VERIFICATION == "verification"
    assert ApiScope.EXPERIENCE == "experience"
    assert ApiScope.AUTOMATION == "automation"
    assert ApiScope.HEALTH == "health"


def test_api_key_metadata_lifecycle_properties():
    """Verify active/expired/revoked state calculations on ApiKeyMetadata."""
    now = datetime.now(timezone.utc)
    # Active key
    active_key = ApiKeyMetadata(
        key_id="k1",
        name="Active Key",
        prefix="xrn_live_abc1...",
        key_hash="hash123",
        salt="salt123",
        scopes=["*"],
    )
    assert active_key.is_active is True

    # Revoked key
    revoked_key = ApiKeyMetadata(
        key_id="k2",
        name="Revoked Key",
        prefix="xrn_live_abc2...",
        key_hash="hash123",
        salt="salt123",
        revoked_at=now,
    )
    assert revoked_key.is_active is False

    # Expired key
    expired_key = ApiKeyMetadata(
        key_id="k3",
        name="Expired Key",
        prefix="xrn_live_abc3...",
        key_hash="hash123",
        salt="salt123",
        expires_at=now - timedelta(seconds=10),
    )
    assert expired_key.is_active is False

    # Future expiration key
    future_key = ApiKeyMetadata(
        key_id="k4",
        name="Future Expiration Key",
        prefix="xrn_live_abc4...",
        key_hash="hash123",
        salt="salt123",
        expires_at=now + timedelta(days=30),
    )
    assert future_key.is_active is True


def test_api_request_auth_header_extraction():
    """Verify Bearer token and X-API-Key extraction in ApiRequest."""
    # Bearer header
    req1 = ApiRequest(
        endpoint="/v1/research",
        headers={"Authorization": "Bearer xrn_live_secret123"},
    )
    assert req1.api_key == "xrn_live_secret123"

    # X-API-Key header
    req2 = ApiRequest(
        endpoint="/v1/data",
        headers={"X-API-Key": "xrn_test_key456"},
    )
    assert req2.api_key == "xrn_test_key456"

    # Direct api_key parameter takes precedence
    req3 = ApiRequest(
        endpoint="/v1/coding",
        api_key="xrn_direct_key",
        headers={"Authorization": "Bearer other"},
    )
    assert req3.api_key == "xrn_direct_key"


def test_api_response_and_error_structure():
    """Verify structured response and error models."""
    err = ApiError(
        code="UNAUTHORIZED",
        message="Invalid credentials",
        status_code=401,
        request_id="req_999",
    )
    resp = ApiResponse(
        request_id="req_999",
        status_code=401,
        success=False,
        error=err,
    )
    assert resp.success is False
    assert resp.status_code == 401
    assert resp.error is not None
    assert resp.error.code == "UNAUTHORIZED"
    assert resp.version == "v1"
