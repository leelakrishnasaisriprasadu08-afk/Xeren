"""High-level API Gateway coordinating authentication, rate limiting, validation, dispatching, and sanitization."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from xeren.plugins.api.schemas import (
    ApiError,
    ApiHealthReport,
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyMetadata,
    ApiRequest,
    ApiResponse,
    ApiScope,
)
from xeren.plugins.api.tools.auth import ApiKeyManagerTool
from xeren.plugins.api.tools.limiter import BaseRateLimiter, SlidingWindowRateLimiter
from xeren.plugins.api.tools.redactor import ApiSecretRedactorTool
from xeren.plugins.api.tools.validator import RequestValidatorTool

logger = logging.getLogger("xeren.plugins.api.tools.gateway")


class ApiGatewayTool:
    """
    Primary entrypoint and routing authority for external communications with Xeren.

    Architecture Flow:
        External Client
        → Xeren API #10
        → Secret Redaction
        → Request Validation
        → API Key Authentication / Scoped Authorization
        → Rate Limiting
        → Xeren Core
        → Plugin Manager
        → Required Plugin / Automation #9 when needed
        → Verification #7 when needed
        → Experience #8 when learning from the outcome is appropriate
        → Xeren Core
        → API Response

    Note:
        - Automation (#9), Verification (#7), and Experience (#8) are modular and invoked
          only when needed by task intent, NOT as a mandatory linear chain for every request.
        - Simple request: API → Core → Target Plugin → Verification (if required) → Response
        - Automated task: API → Core → Automation #9 → Plugins → Verification #7 → Experience #8 → Response
    """

    def __init__(
        self,
        auth_manager: Optional[ApiKeyManagerTool] = None,
        validator: Optional[RequestValidatorTool] = None,
        rate_limiter: Optional[BaseRateLimiter] = None,
        redactor: Optional[ApiSecretRedactorTool] = None,
        core_dispatcher: Optional[Callable[[str, Any], Any]] = None,
    ) -> None:
        self.auth_manager = auth_manager or ApiKeyManagerTool()
        self.validator = validator or RequestValidatorTool()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()
        self.redactor = redactor or ApiSecretRedactorTool()
        self.core_dispatcher = core_dispatcher
        self._start_time = time.monotonic()
        self._request_audit_log: List[Dict[str, Any]] = []

    def set_core_dispatcher(self, dispatcher: Callable[[str, Any], Any]) -> None:
        """Attach or update the downstream dispatcher targeting Xeren Core."""
        self.core_dispatcher = dispatcher

    def handle_request(self, request: ApiRequest) -> ApiResponse:
        """
        Synchronously process an incoming API request through the full security pipeline:
        Audit Log -> Request Validation -> Authentication -> Rate Limiting -> Scope Gate -> Core Execution -> Sanitized Response.
        """
        start_mono = time.perf_counter()
        clean_endpoint = request.endpoint.split("?")[0].rstrip("/")
        rate_headers: Dict[str, Any] = {}

        # 1. Audit Logging (Guaranteed zero plaintext secret exposure)
        sanitized_headers = self.redactor.sanitize_headers(request.headers)
        self._log_audit_event(
            event="request_received",
            request_id=request.request_id,
            endpoint=clean_endpoint,
            method=request.method,
            client_ip=request.client_ip,
            headers=sanitized_headers,
        )

        # 2. Request Validation (Endpoint syntax, HTTP method, payload size)
        is_valid, val_error = self.validator.validate_request(request)
        if not is_valid and val_error:
            return self._format_error_response(val_error, start_mono)

        # 3. Authentication & Rate Limiting
        is_public_endpoint = clean_endpoint == "/v1/health" and request.method.upper() == "GET"
        authenticated_key: Optional[ApiKeyMetadata] = None

        if not is_public_endpoint:
            # Extract raw API key
            raw_key = request.api_key
            if not raw_key:
                err = ApiError(
                    code="UNAUTHORIZED",
                    message="Missing Xeren API key. Provide via 'Authorization: Bearer <key>' or 'X-API-Key: <key>' header.",
                    status_code=401,
                    request_id=request.request_id,
                )
                return self._format_error_response(err, start_mono)

            # Authenticate credentials
            is_auth, key_meta, auth_err = self.auth_manager.validate_key(raw_key)
            if not is_auth or not key_meta:
                err = ApiError(
                    code="UNAUTHORIZED",
                    message=auth_err or "Invalid or unverified API key credentials",
                    status_code=401,
                    request_id=request.request_id,
                )
                return self._format_error_response(err, start_mono)

            authenticated_key = key_meta

            # Enforce Rate Limiting
            rate_limit_ceiling = key_meta.rate_limit_per_minute
            allowed, limit_info = self.rate_limiter.check_rate_limit(
                key_meta.key_id, rate_limit_ceiling
            )
            rate_headers = {
                "X-RateLimit-Limit": limit_info.get("limit"),
                "X-RateLimit-Remaining": limit_info.get("remaining"),
                "X-RateLimit-Reset": limit_info.get("reset_seconds"),
            }

            if not allowed:
                err = ApiError(
                    code="RATE_LIMITED",
                    message=f"Rate limit exceeded ({rate_limit_ceiling} requests/min). Please back off.",
                    status_code=429,
                    details=limit_info,
                    request_id=request.request_id,
                )
                res = self._format_error_response(err, start_mono)
                res.metadata.update(rate_headers)
                return res

            # 4. Scoped Authorization Check
            required_scope = self.validator.get_required_scope(clean_endpoint)
            if required_scope and not self.auth_manager.has_permission(key_meta, required_scope):
                err = ApiError(
                    code="FORBIDDEN",
                    message=(
                        f"API key '{key_meta.name}' lacks required scope '{required_scope}'. "
                        f"Granted scopes: {key_meta.scopes}"
                    ),
                    status_code=403,
                    request_id=request.request_id,
                )
                res = self._format_error_response(err, start_mono)
                res.metadata.update(rate_headers)
                return res

        # 5. Core Route Execution
        try:
            output_data, status_code = self._dispatch_route(clean_endpoint, request, authenticated_key)
            # Scrub output data to redact any leaked paths or sensitive tokens
            clean_output = self.redactor.sanitize_payload(output_data)

            elapsed_ms = round((time.perf_counter() - start_mono) * 1000.0, 2)
            response = ApiResponse(
                request_id=request.request_id,
                status_code=status_code,
                success=True,
                data=clean_output,
                latency_ms=elapsed_ms,
                version="v1",
                metadata=rate_headers,
            )
            self._log_audit_event(
                event="request_completed",
                request_id=request.request_id,
                status_code=status_code,
                latency_ms=elapsed_ms,
            )
            return response

        except Exception as exc:
            logger.exception("Internal error processing route '%s'", clean_endpoint)
            sanitized_msg = self.redactor.sanitize_text(str(exc)) or "Internal server error"
            # Strip raw stack trace; return clean error code
            err = ApiError(
                code="INTERNAL_ERROR",
                message=sanitized_msg,
                status_code=500,
                request_id=request.request_id,
            )
            res = self._format_error_response(err, start_mono)
            res.metadata.update(rate_headers)
            return res

    async def ahandle_request(self, request: ApiRequest) -> ApiResponse:
        """Asynchronously process an API request."""
        return await asyncio.to_thread(self.handle_request, request)

    def _dispatch_route(
        self,
        endpoint: str,
        request: ApiRequest,
        key_meta: Optional[ApiKeyMetadata],
    ) -> Tuple[Any, int]:
        """Dispatch validated request to internal handlers or Core plugins."""
        # 1. Health Status endpoint
        if endpoint == "/v1/health":
            uptime = round(time.monotonic() - self._start_time, 2)
            plugin_health = {}
            active_plugins = []
            if self.core_dispatcher:
                try:
                    report = self.core_dispatcher("health", {})
                    if isinstance(report, dict):
                        plugin_health = report.get("plugins", {})
                        active_plugins = list(plugin_health.keys())
                except Exception:
                    pass

            report_obj = ApiHealthReport(
                status="healthy",
                version="v1",
                uptime_seconds=uptime,
                active_plugins=active_plugins,
                plugins=plugin_health,
            )
            return report_obj.model_dump(mode="python"), 200

        # 2. Key Management Routes (/v1/keys/*)
        if endpoint in ("/v1/keys", "/v1/keys/create"):
            if request.method.upper() == "GET":
                keys = self.auth_manager.store.list_keys(include_revoked=True)
                return [k.model_dump(mode="python") for k in keys], 200
            elif request.method.upper() == "POST":
                body = request.body or {}
                name = body.get("name") or "External Client Key"
                scopes = body.get("scopes") or [ApiScope.ALL.value]
                rate_limit = body.get("rate_limit_per_minute") or 60
                expires_in_days = body.get("expires_in_days")
                meta, raw = self.auth_manager.generate_key(
                    name=name,
                    scopes=scopes,
                    rate_limit_per_minute=rate_limit,
                    expires_in_days=expires_in_days,
                    metadata=body.get("metadata", {}),
                )
                created_res = ApiKeyCreatedResponse(
                    key_id=meta.key_id,
                    name=meta.name,
                    raw_key=raw,
                    prefix=meta.prefix,
                    scopes=meta.scopes,
                    rate_limit_per_minute=meta.rate_limit_per_minute,
                    created_at=meta.created_at,
                    expires_at=meta.expires_at,
                )
                return created_res.model_dump(mode="python"), 201

        if endpoint == "/v1/keys/rotate":
            body = request.body or {}
            target_key_id = body.get("key_id")
            if not target_key_id:
                raise ValueError("Body must contain 'key_id' to rotate.")
            grace = float(body.get("grace_period_seconds", 0.0))
            new_meta, new_raw = self.auth_manager.rotate_key(target_key_id, grace_period_seconds=grace)
            rotated_res = ApiKeyCreatedResponse(
                key_id=new_meta.key_id,
                name=new_meta.name,
                raw_key=new_raw,
                prefix=new_meta.prefix,
                scopes=new_meta.scopes,
                rate_limit_per_minute=new_meta.rate_limit_per_minute,
                created_at=new_meta.created_at,
                expires_at=new_meta.expires_at,
            )
            return rotated_res.model_dump(mode="python"), 200

        if endpoint == "/v1/keys/revoke":
            body = request.body or {}
            target_key_id = body.get("key_id")
            if not target_key_id:
                raise ValueError("Body must contain 'key_id' to revoke.")
            reason = body.get("reason")
            success = self.auth_manager.revoke_key(target_key_id, reason=reason)
            return {"key_id": target_key_id, "revoked": success}, 200

        # 3. Downstream Core Plugin routes (/v1/research, /v1/data, etc.)
        plugin_name = endpoint.replace("/v1/", "")
        payload = request.body or {}

        if not self.core_dispatcher:
            # Fallback mock/echo response when Core dispatcher is not wired directly
            return {
                "dispatched_route": endpoint,
                "plugin": plugin_name,
                "input": payload,
                "status": "simulated_success",
            }, 200

        # Execute through Core dispatcher
        output = self.core_dispatcher(plugin_name, payload)
        # If output is a Pydantic model, dump to python dict
        if hasattr(output, "model_dump"):
            output = output.model_dump(mode="python")
        return output, 200

    def _format_error_response(self, error: ApiError, start_mono: float) -> ApiResponse:
        """Generate a clean, sanitized error response object."""
        elapsed_ms = round((time.perf_counter() - start_mono) * 1000.0, 2)
        # Redact error message
        clean_msg = self.redactor.sanitize_text(error.message) or "Error"
        clean_err = ApiError(
            code=error.code,
            message=clean_msg,
            status_code=error.status_code,
            details=self.redactor.sanitize_payload(error.details) if error.details else None,
            request_id=error.request_id,
        )
        return ApiResponse(
            request_id=error.request_id or "unknown",
            status_code=error.status_code,
            success=False,
            error=clean_err,
            latency_ms=elapsed_ms,
            version="v1",
        )

    def _log_audit_event(self, event: str, **kwargs: Any) -> None:
        """Record an internal audit log entry without leaking sensitive credentials."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **self.redactor.sanitize_payload(kwargs),
        }
        self._request_audit_log.append(entry)
        if len(self._request_audit_log) > 500:
            self._request_audit_log = self._request_audit_log[-500:]

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent sanitized audit logs."""
        return self._request_audit_log[-limit:]

    # -------------------------------------------------------------------------
    # ASGI 3.0 Adapter (Enables plug-and-play mount in Uvicorn, FastAPI, Starlette)
    # -------------------------------------------------------------------------
    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        """ASGI 3.0 compatible application entrypoint."""
        if scope["type"] != "http":
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/v1/health")
        raw_headers = scope.get("headers", [])

        # Parse headers
        headers: Dict[str, str] = {}
        for h_k, h_v in raw_headers:
            try:
                headers[h_k.decode("latin1")] = h_v.decode("latin1")
            except Exception:
                pass

        # Parse body
        body_bytes = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            body_bytes.extend(message.get("body", b""))
            more_body = message.get("more_body", False)

        body_data = None
        if body_bytes:
            try:
                body_data = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body_data = body_bytes.decode("utf-8", errors="replace")

        client_ip = scope.get("client", ["127.0.0.1"])[0]

        req = ApiRequest(
            endpoint=path,
            method=method,
            headers=headers,
            body=body_data,
            client_ip=client_ip,
        )

        response = await self.ahandle_request(req)
        resp_json = response.model_dump_json()

        # Send ASGI HTTP response
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"x-request-id", response.request_id.encode("ascii")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": resp_json.encode("utf-8"),
            }
        )


__all__ = ["ApiGatewayTool"]
