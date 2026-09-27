"""Request validation engine enforcing route matching, HTTP methods, and payload size ceilings."""

import json
from typing import Any, Dict, Optional, Set, Tuple

from xeren.plugins.api.schemas import ApiError, ApiRequest, ApiScope

DEFAULT_MAX_BODY_SIZE = 2 * 1024 * 1024  # 2 MB

# Canonical mapping of supported /v1 API routes to required permissions
ROUTE_SCOPE_MAPPING: Dict[str, str] = {
    "/v1/health": ApiScope.HEALTH.value,
    "/v1/research": ApiScope.RESEARCH.value,
    "/v1/knowledge": ApiScope.KNOWLEDGE.value,
    "/v1/coding": ApiScope.CODING.value,
    "/v1/website": ApiScope.WEBSITE.value,
    "/v1/data": ApiScope.DATA.value,
    "/v1/file": ApiScope.FILE.value,
    "/v1/verification": ApiScope.VERIFICATION.value,
    "/v1/experience": ApiScope.EXPERIENCE.value,
    "/v1/automation": ApiScope.AUTOMATION.value,
    "/v1/keys": ApiScope.ADMIN.value,
    "/v1/keys/create": ApiScope.ADMIN.value,
    "/v1/keys/rotate": ApiScope.ADMIN.value,
    "/v1/keys/revoke": ApiScope.ADMIN.value,
}

ALLOWED_METHODS: Set[str] = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"}


class RequestValidationError(Exception):
    """Raised when an API request fails validation checks."""

    def __init__(self, message: str, status_code: int = 400, code: str = "VALIDATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class RequestValidatorTool:
    """Validates endpoint paths, HTTP verbs, payload size limits, and checks for malicious inputs."""

    def __init__(self, max_body_size_bytes: int = DEFAULT_MAX_BODY_SIZE) -> None:
        self.max_body_size_bytes = max_body_size_bytes

    def validate_request(self, request: ApiRequest) -> Tuple[bool, Optional[ApiError]]:
        """
        Validate incoming request parameters, endpoint structure, and size boundaries.

        Returns:
            Tuple of (is_valid, Optional[ApiError]).
        """
        # 1. Null-byte rejection
        if "\0" in request.endpoint:
            return False, ApiError(
                code="INVALID_ENDPOINT",
                message="Null bytes in endpoint route are strictly prohibited",
                status_code=400,
                request_id=request.request_id,
            )

        # 2. HTTP Method validation
        method_upper = request.method.upper()
        if method_upper not in ALLOWED_METHODS:
            return False, ApiError(
                code="METHOD_NOT_ALLOWED",
                message=f"HTTP method '{request.method}' is not supported",
                status_code=405,
                request_id=request.request_id,
            )

        # 3. Endpoint routing validation
        clean_endpoint = request.endpoint.split("?")[0].rstrip("/")
        if not clean_endpoint.startswith("/v1"):
            return False, ApiError(
                code="UNSUPPORTED_API_VERSION",
                message=f"Endpoint '{request.endpoint}' must target a supported API version (e.g. '/v1/...')",
                status_code=404,
                request_id=request.request_id,
            )

        if clean_endpoint not in ROUTE_SCOPE_MAPPING:
            return False, ApiError(
                code="NOT_FOUND",
                message=f"Unknown API endpoint '{clean_endpoint}'",
                status_code=404,
                request_id=request.request_id,
            )

        # 4. Request payload size validation
        if request.body is not None:
            size = self._estimate_size(request.body)
            if size > self.max_body_size_bytes:
                return False, ApiError(
                    code="PAYLOAD_TOO_LARGE",
                    message=(
                        f"Request payload size ({size} bytes) exceeds the allowed limit of "
                        f"{self.max_body_size_bytes} bytes (2 MB)"
                    ),
                    status_code=413,
                    request_id=request.request_id,
                )

        return True, None

    def get_required_scope(self, endpoint: str) -> Optional[str]:
        """Lookup the required scope for a given route endpoint."""
        clean_endpoint = endpoint.split("?")[0].rstrip("/")
        return ROUTE_SCOPE_MAPPING.get(clean_endpoint)

    @staticmethod
    def _estimate_size(val: Any) -> int:
        """Estimate the byte size of a request payload."""
        if isinstance(val, (bytes, bytearray)):
            return len(val)
        if isinstance(val, str):
            return len(val.encode("utf-8"))
        try:
            return len(json.dumps(val).encode("utf-8"))
        except Exception:
            return 1024  # Fallback estimate for un-serializable objects


__all__ = [
    "RequestValidatorTool",
    "RequestValidationError",
    "ROUTE_SCOPE_MAPPING",
    "DEFAULT_MAX_BODY_SIZE",
]
