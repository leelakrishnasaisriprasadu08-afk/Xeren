"""Pydantic schemas and typed data models for the Xeren API / Communication Plugin."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field, model_validator


class ApiOperation(str, Enum):
    """The 10 core operations supported by ApiPlugin."""

    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    API_KEY_AUTHENTICATION = "api_key_authentication"
    API_KEY_ROTATION = "api_key_rotation"
    API_KEY_REVOCATION = "api_key_revocation"
    SCOPED_PERMISSIONS = "scoped_permissions"
    REQUEST_VALIDATION = "request_validation"
    RATE_LIMITING = "rate_limiting"
    REQUEST_LOGGING = "request_logging"
    HEALTH_STATUS = "health_status"


class ApiScope(str, Enum):
    """Granular permission scopes for Xeren API keys."""

    ALL = "*"
    ADMIN = "admin"
    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    CODING = "coding"
    WEBSITE = "website"
    DATA = "data"
    FILE = "file"
    VERIFICATION = "verification"
    EXPERIENCE = "experience"
    AUTOMATION = "automation"
    HEALTH = "health"


class ApiKeyEnvironment(str, Enum):
    """Environment prefix for Xeren API credentials."""

    LIVE = "live"
    TEST = "test"


class ApiKeyMetadata(BaseModel):
    """Secure metadata record for a Xeren API key.
    
    CRITICAL: Never contains the plaintext key. Only holds salted cryptographic hash.
    """

    key_id: str = Field(
        default_factory=lambda: f"key_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for the API key metadata record",
    )
    name: str = Field(..., description="Human-readable label for key (e.g. 'Production Backend')")
    prefix: str = Field(..., description="Safe identifier prefix (e.g. 'xrn_live_a1b2')")
    key_hash: str = Field(..., description="Salted HMAC-SHA256 hex digest of the raw key")
    salt: str = Field(..., description="Cryptographic salt used for hashing")
    scopes: List[str] = Field(default_factory=lambda: ["*"], description="Authorized permission scopes")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000, description="Max allowed requests/min")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC creation timestamp"
    )
    expires_at: Optional[datetime] = Field(default=None, description="Optional UTC expiration timestamp")
    revoked_at: Optional[datetime] = Field(default=None, description="Optional UTC revocation timestamp")
    last_used_at: Optional[datetime] = Field(default=None, description="Optional UTC last used timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary non-secret metadata")

    @property
    def is_active(self) -> bool:
        """Return True if the key is not revoked and not expired."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


class ApiKeyCreateRequest(BaseModel):
    """Request parameters for generating a new Xeren API key."""

    name: str = Field(..., description="Friendly label for the API key")
    scopes: List[str] = Field(default_factory=lambda: ["*"], description="List of scopes to grant")
    rate_limit_per_minute: int = Field(default=60, ge=1, description="Rate limit ceiling per minute")
    expires_in_days: Optional[int] = Field(default=None, ge=1, description="Optional lifetime in days")
    environment: ApiKeyEnvironment = Field(
        default=ApiKeyEnvironment.LIVE, description="Environment prefix ('live' or 'test')"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")


class ApiKeyCreatedResponse(BaseModel):
    """Response returned upon key creation.
    
    WARNING: The `raw_key` is returned ONLY once upon creation and cannot be recovered later.
    """

    key_id: str = Field(..., description="Unique key ID")
    name: str = Field(..., description="Key label")
    raw_key: str = Field(..., description="Plaintext API key (never stored, shown once)")
    prefix: str = Field(..., description="Display prefix")
    scopes: List[str] = Field(..., description="Granted scopes")
    rate_limit_per_minute: int = Field(..., description="Rate limit")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")


class ApiKeyRotateRequest(BaseModel):
    """Request parameters for rotating an existing API key."""

    key_id: str = Field(..., description="ID of key to rotate")
    grace_period_seconds: float = Field(
        default=0.0, ge=0.0, description="Optional seconds old key remains valid before deactivation"
    )


class ApiKeyRevokeRequest(BaseModel):
    """Request parameters for revoking an API key immediately."""

    key_id: str = Field(..., description="ID of key to revoke")
    reason: Optional[str] = Field(default=None, description="Optional diagnostic revocation reason")


class ApiError(BaseModel):
    """Standardized API error structure for client-facing responses."""

    code: str = Field(..., description="Machine-readable error code (e.g. 'UNAUTHORIZED')")
    message: str = Field(..., description="Sanitized, human-readable error description")
    status_code: int = Field(default=400, description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured details")
    request_id: Optional[str] = Field(default=None, description="Request correlation identifier")


class ApiRequest(BaseModel):
    """Canonical model for incoming external API requests."""

    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}",
        description="Unique request correlation ID",
    )
    endpoint: str = Field(..., description="Target route path (e.g. '/v1/research')")
    method: str = Field(default="POST", description="HTTP method ('GET', 'POST', etc.)")
    headers: Dict[str, str] = Field(default_factory=dict, description="Incoming HTTP request headers")
    params: Dict[str, Any] = Field(default_factory=dict, description="URL query parameters")
    body: Optional[Any] = Field(default=None, description="Request body payload")
    client_ip: Optional[str] = Field(default=None, description="Client IP address for rate limiting")
    api_key: Optional[str] = Field(default=None, description="Raw Xeren API key if extracted directly")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual request metadata")

    @model_validator(mode="before")
    @classmethod
    def _extract_auth_header(cls, data: Any) -> Any:
        if isinstance(data, dict):
            headers = data.get("headers") or {}
            # Check Authorization: Bearer <key> or X-API-Key: <key>
            if not data.get("api_key"):
                auth_val = headers.get("Authorization") or headers.get("authorization")
                if auth_val and auth_val.startswith("Bearer "):
                    data["api_key"] = auth_val[7:].strip()
                elif headers.get("X-API-Key"):
                    data["api_key"] = headers.get("X-API-Key")
                elif headers.get("x-api-key"):
                    data["api_key"] = headers.get("x-api-key")
        return data


class ApiResponse(BaseModel):
    """Standardized API response payload (/v1 format)."""

    request_id: str = Field(..., description="Correlating request identifier")
    status_code: int = Field(default=200, description="HTTP response status code")
    success: bool = Field(default=True, description="Whether the operation succeeded")
    data: Optional[Any] = Field(default=None, description="Successful output data payload")
    error: Optional[ApiError] = Field(default=None, description="Sanitized error object if failed")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Total request processing time in ms")
    version: str = Field(default="v1", description="API version tag")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata and rate headers")


class ApiHealthReport(BaseModel):
    """Payload representing API gateway and backend subsystem health."""

    status: str = Field(default="healthy", description="Overall service status ('healthy'/'degraded')")
    version: str = Field(default="v1", description="API version")
    uptime_seconds: float = Field(default=0.0, description="Seconds since API startup")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC report timestamp"
    )
    active_plugins: List[str] = Field(default_factory=list, description="Registered backend plugins")
    plugins: Dict[str, Any] = Field(default_factory=dict, description="Subsystem health statuses")


class ApiInput(BaseModel):
    """Input parameters for ApiPlugin operations."""

    operation: ApiOperation = Field(
        default=ApiOperation.API_REQUEST, description="API operation to execute"
    )
    request: Optional[ApiRequest] = Field(default=None, description="Incoming API request to process")
    api_key: Optional[str] = Field(default=None, description="Raw API key string to authenticate")
    key_id: Optional[str] = Field(default=None, description="Target key ID for inspection, rotation, or revocation")
    create_request: Optional[ApiKeyCreateRequest] = Field(
        default=None, description="Parameters for key generation"
    )
    rotate_request: Optional[ApiKeyRotateRequest] = Field(
        default=None, description="Parameters for key rotation"
    )
    revoke_request: Optional[ApiKeyRevokeRequest] = Field(
        default=None, description="Parameters for key revocation"
    )
    scope_to_check: Optional[str] = Field(default=None, description="Target scope to test against key")
    endpoint: Optional[str] = Field(default=None, description="Endpoint path alias")
    method: Optional[str] = Field(default=None, description="HTTP method alias")
    body: Optional[Any] = Field(default=None, description="Body payload alias")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Headers alias")
    client_ip: Optional[str] = Field(default=None, description="Client IP alias")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary configuration metadata")


class ApiResult(BaseModel):
    """Result payload returned by ApiPlugin operations."""

    operation: ApiOperation = Field(..., description="The executed operation")
    success: bool = Field(default=True, description="Whether the operation succeeded")
    response: Optional[ApiResponse] = Field(default=None, description="Processed API response object")
    key_metadata: Optional[ApiKeyMetadata] = Field(default=None, description="API key metadata record")
    created_key: Optional[ApiKeyCreatedResponse] = Field(
        default=None, description="Plaintext key response (returned only upon creation)"
    )
    is_authenticated: Optional[bool] = Field(default=None, description="Authentication evaluation result")
    is_authorized: Optional[bool] = Field(default=None, description="Scope authorization evaluation result")
    is_valid: Optional[bool] = Field(default=None, description="Request validation evaluation result")
    is_rate_limited: Optional[bool] = Field(default=None, description="Rate limit evaluation result")
    health_report: Optional[ApiHealthReport] = Field(default=None, description="Service health report")
    error: Optional[str] = Field(default=None, description="Diagnostic error description if failed")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Operation duration in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operation metrics and metadata")


__all__ = [
    "ApiOperation",
    "ApiScope",
    "ApiKeyEnvironment",
    "ApiKeyMetadata",
    "ApiKeyCreateRequest",
    "ApiKeyCreatedResponse",
    "ApiKeyRotateRequest",
    "ApiKeyRevokeRequest",
    "ApiError",
    "ApiRequest",
    "ApiResponse",
    "ApiHealthReport",
    "ApiInput",
    "ApiResult",
]
