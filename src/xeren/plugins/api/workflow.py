"""Workflow orchestrator coordinating operations for the Xeren API / Communication Plugin."""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional

from xeren.plugins.api.registry import ApiToolRegistry
from xeren.plugins.api.schemas import (
    ApiError,
    ApiHealthReport,
    ApiKeyCreatedResponse,
    ApiKeyMetadata,
    ApiInput,
    ApiOperation,
    ApiRequest,
    ApiResponse,
    ApiResult,
    ApiScope,
)
from xeren.plugins.contract import PluginExecutionContext


class ApiWorkflow:
    """Dispatches and orchestrates all 10 API operations."""

    def __init__(self, registry: ApiToolRegistry) -> None:
        self.registry = registry

    def execute(self, input_data: ApiInput, context: Optional[PluginExecutionContext] = None) -> ApiResult:
        """Synchronously execute an API operation."""
        start_mono = time.perf_counter()
        op = input_data.operation

        try:
            if op == ApiOperation.API_REQUEST:
                res = self._execute_request(input_data)
            elif op == ApiOperation.API_RESPONSE:
                res = self._execute_response(input_data)
            elif op == ApiOperation.API_KEY_AUTHENTICATION:
                res = self._execute_auth(input_data)
            elif op == ApiOperation.API_KEY_ROTATION:
                res = self._execute_rotation(input_data)
            elif op == ApiOperation.API_KEY_REVOCATION:
                res = self._execute_revocation(input_data)
            elif op == ApiOperation.SCOPED_PERMISSIONS:
                res = self._execute_permissions(input_data)
            elif op == ApiOperation.REQUEST_VALIDATION:
                res = self._execute_validation(input_data)
            elif op == ApiOperation.RATE_LIMITING:
                res = self._execute_rate_limiting(input_data)
            elif op == ApiOperation.REQUEST_LOGGING:
                res = self._execute_logging(input_data)
            elif op == ApiOperation.HEALTH_STATUS:
                res = self._execute_health(input_data)
            else:
                return ApiResult(
                    operation=op,
                    success=False,
                    error=f"Unsupported operation '{op.value}'.",
                )

            elapsed_ms = round((time.perf_counter() - start_mono) * 1000.0, 2)
            res.latency_ms = elapsed_ms
            return res

        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_mono) * 1000.0, 2)
            return ApiResult(
                operation=op,
                success=False,
                error=str(exc),
                latency_ms=elapsed_ms,
            )

    async def aexecute(self, input_data: ApiInput, context: Optional[PluginExecutionContext] = None) -> ApiResult:
        """Asynchronously execute an API operation."""
        return await asyncio.to_thread(self.execute, input_data, context)

    # -------------------------------------------------------------------------
    # Individual Operation Handlers
    # -------------------------------------------------------------------------
    def _execute_request(self, input_data: ApiInput) -> ApiResult:
        req = input_data.request
        if not req:
            if input_data.endpoint:
                req = ApiRequest(
                    endpoint=input_data.endpoint,
                    method=input_data.method or "POST",
                    body=input_data.body,
                    headers=input_data.headers or {},
                    client_ip=input_data.client_ip,
                    api_key=input_data.api_key,
                )
            else:
                return ApiResult(
                    operation=input_data.operation,
                    success=False,
                    error="ApiRequest payload or endpoint is required for API_REQUEST.",
                )

        response = self.registry.gateway.handle_request(req)
        return ApiResult(
            operation=input_data.operation,
            success=response.success,
            response=response,
            error=response.error.message if response.error else None,
        )

    def _execute_response(self, input_data: ApiInput) -> ApiResult:
        # Wrap or format data into a standardized response
        body = input_data.body
        status = 200
        resp = ApiResponse(
            request_id=f"fmt_{int(time.time()*1000)}",
            status_code=status,
            success=True,
            data=body,
            version="v1",
        )
        return ApiResult(
            operation=input_data.operation,
            success=True,
            response=resp,
        )

    def _execute_auth(self, input_data: ApiInput) -> ApiResult:
        raw_key = input_data.api_key
        if not raw_key and input_data.request:
            raw_key = input_data.request.api_key

        is_auth, meta, err = self.registry.auth_manager.validate_key(raw_key)
        return ApiResult(
            operation=input_data.operation,
            success=is_auth,
            is_authenticated=is_auth,
            key_metadata=meta,
            error=err,
        )

    def _execute_rotation(self, input_data: ApiInput) -> ApiResult:
        key_id = input_data.key_id
        grace = 0.0
        if input_data.rotate_request:
            key_id = input_data.rotate_request.key_id
            grace = input_data.rotate_request.grace_period_seconds

        if not key_id:
            return ApiResult(
                operation=input_data.operation,
                success=False,
                error="key_id is required for API_KEY_ROTATION.",
            )

        new_meta, new_raw = self.registry.auth_manager.rotate_key(key_id, grace_period_seconds=grace)
        created_res = ApiKeyCreatedResponse(
            key_id=new_meta.key_id,
            name=new_meta.name,
            raw_key=new_raw,
            prefix=new_meta.prefix,
            scopes=new_meta.scopes,
            rate_limit_per_minute=new_meta.rate_limit_per_minute,
            created_at=new_meta.created_at,
            expires_at=new_meta.expires_at,
        )
        return ApiResult(
            operation=input_data.operation,
            success=True,
            key_metadata=new_meta,
            created_key=created_res,
        )

    def _execute_revocation(self, input_data: ApiInput) -> ApiResult:
        key_id = input_data.key_id
        reason = None
        if input_data.revoke_request:
            key_id = input_data.revoke_request.key_id
            reason = input_data.revoke_request.reason

        if not key_id:
            return ApiResult(
                operation=input_data.operation,
                success=False,
                error="key_id is required for API_KEY_REVOCATION.",
            )

        success = self.registry.auth_manager.revoke_key(key_id, reason=reason)
        meta = self.registry.store.get_key(key_id)
        return ApiResult(
            operation=input_data.operation,
            success=success,
            key_metadata=meta,
            error=None if success else f"API key '{key_id}' not found.",
        )

    def _execute_permissions(self, input_data: ApiInput) -> ApiResult:
        key_id = input_data.key_id
        scope_req = input_data.scope_to_check or "*"
        meta = None

        if key_id:
            meta = self.registry.store.get_key(key_id)
        elif input_data.api_key:
            _, meta, _ = self.registry.auth_manager.validate_key(input_data.api_key)

        if not meta:
            return ApiResult(
                operation=input_data.operation,
                success=False,
                is_authorized=False,
                error="Valid key_id or api_key required to check scopes.",
            )

        is_auth = self.registry.auth_manager.has_permission(meta, scope_req)
        return ApiResult(
            operation=input_data.operation,
            success=True,
            is_authorized=is_auth,
            key_metadata=meta,
            metadata={"checked_scope": scope_req, "granted_scopes": meta.scopes},
        )

    def _execute_validation(self, input_data: ApiInput) -> ApiResult:
        req = input_data.request
        if not req:
            req = ApiRequest(
                endpoint=input_data.endpoint or "/v1/health",
                method=input_data.method or "GET",
                body=input_data.body,
                headers=input_data.headers or {},
            )

        is_valid, err = self.registry.validator.validate_request(req)
        return ApiResult(
            operation=input_data.operation,
            success=is_valid,
            is_valid=is_valid,
            error=err.message if err else None,
        )

    def _execute_rate_limiting(self, input_data: ApiInput) -> ApiResult:
        ident = input_data.key_id or input_data.client_ip or "default_client"
        limit = 60
        if input_data.key_id:
            meta = self.registry.store.get_key(input_data.key_id)
            if meta:
                limit = meta.rate_limit_per_minute

        allowed, info = self.registry.rate_limiter.check_rate_limit(ident, limit)
        return ApiResult(
            operation=input_data.operation,
            success=True,
            is_rate_limited=not allowed,
            metadata={"identifier": ident, **info},
        )

    def _execute_logging(self, input_data: ApiInput) -> ApiResult:
        limit = input_data.metadata.get("limit", 50)
        logs = self.registry.gateway.get_audit_logs(limit=limit)
        return ApiResult(
            operation=input_data.operation,
            success=True,
            metadata={"audit_logs_count": len(logs), "audit_logs": logs},
        )

    def _execute_health(self, input_data: ApiInput) -> ApiResult:
        req = ApiRequest(endpoint="/v1/health", method="GET")
        resp = self.registry.gateway.handle_request(req)
        report = None
        if resp.data and isinstance(resp.data, dict):
            report = ApiHealthReport.model_validate(resp.data)
        return ApiResult(
            operation=input_data.operation,
            success=resp.success,
            response=resp,
            health_report=report,
        )


__all__ = ["ApiWorkflow"]
