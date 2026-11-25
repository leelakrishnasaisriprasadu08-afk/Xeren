"""API / Communication Plugin implementation adhering strictly to the Xeren BasePlugin contract."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from xeren.plugins.api.manifest import API_PLUGIN_MANIFEST
from xeren.plugins.api.registry import ApiToolRegistry
from xeren.plugins.api.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyEnvironment,
    ApiKeyMetadata,
    ApiKeyRevokeRequest,
    ApiKeyRotateRequest,
    ApiInput,
    ApiOperation,
    ApiRequest,
    ApiResponse,
    ApiResult,
    ApiScope,
)
from xeren.plugins.api.workflow import ApiWorkflow
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import PluginExecutionError

if TYPE_CHECKING:
    from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.plugins.api.plugin")


class ApiPlugin(BasePlugin):
    """
    Production API gateway and communication plugin for Xeren Core.

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
    """

    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        registry: Optional[ApiToolRegistry] = None,
        workflow: Optional[ApiWorkflow] = None,
    ) -> None:
        self.registry = registry or ApiToolRegistry(plugin_manager=plugin_manager)
        self.workflow = workflow or ApiWorkflow(registry=self.registry)
        self._initialized: bool = True

    @property
    def manifest(self) -> PluginManifest:
        return API_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ApiInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ApiResult

    def set_plugin_manager(self, plugin_manager: PluginManager) -> None:
        """Inject or update the active PluginManager instance."""
        self.registry.set_plugin_manager(plugin_manager)

    def set_core(self, core: Any) -> None:
        """Inject or update the active XerenCore runtime instance."""
        self.registry.set_core(core)

    # -------------------------------------------------------------------------
    # BasePlugin Execution Interface
    # -------------------------------------------------------------------------
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute an API operation."""
        start_time = time.perf_counter()
        try:
            validated_input: ApiInput = self.validate_input(input_data)  # type: ignore
            result: ApiResult = self.workflow.execute(validated_input, context=context)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "is_authenticated": result.is_authenticated,
                    "is_authorized": result.is_authorized,
                    "status_code": result.response.status_code if result.response else None,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("ApiPlugin execution failed: %s", err)
            raise PluginExecutionError(
                f"ApiPlugin execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute an API operation."""
        start_time = time.perf_counter()
        try:
            validated_input: ApiInput = self.validate_input(input_data)  # type: ignore
            result: ApiResult = await self.workflow.aexecute(validated_input, context=context)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=result.success,
                output=result,
                latency_ms=latency_ms,
                error=result.error,
                metadata={
                    "operation": result.operation.value,
                    "is_authenticated": result.is_authenticated,
                    "is_authorized": result.is_authorized,
                    "status_code": result.response.status_code if result.response else None,
                },
            )
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("ApiPlugin async execution failed: %s", err)
            raise PluginExecutionError(
                f"ApiPlugin async execution failed: {err}",
                plugin_name=self.name,
                raw_error=err,
            ) from err

    # -------------------------------------------------------------------------
    # Typed Convenience Methods
    # -------------------------------------------------------------------------
    def handle_request(self, request: ApiRequest) -> ApiResponse:
        """Convenience method to process an API request through the gateway."""
        inp = ApiInput(operation=ApiOperation.API_REQUEST, request=request)
        res = self.workflow.execute(inp)
        if res.response:
            return res.response
        return ApiResponse(
            request_id=request.request_id,
            status_code=500,
            success=False,
            error=None,
        )

    async def ahandle_request(self, request: ApiRequest) -> ApiResponse:
        """Asynchronously process an API request through the gateway."""
        inp = ApiInput(operation=ApiOperation.API_REQUEST, request=request)
        res = await self.workflow.aexecute(inp)
        if res.response:
            return res.response
        return ApiResponse(
            request_id=request.request_id,
            status_code=500,
            success=False,
            error=None,
        )

    def create_api_key(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        rate_limit_per_minute: int = 60,
        expires_in_days: Optional[int] = None,
        environment: ApiKeyEnvironment = ApiKeyEnvironment.LIVE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApiKeyCreatedResponse:
        """Convenience method to generate and store a new API key."""
        meta, raw = self.registry.auth_manager.generate_key(
            name=name,
            scopes=scopes,
            rate_limit_per_minute=rate_limit_per_minute,
            expires_in_days=expires_in_days,
            environment=environment,
            metadata=metadata,
        )
        return ApiKeyCreatedResponse(
            key_id=meta.key_id,
            name=meta.name,
            raw_key=raw,
            prefix=meta.prefix,
            scopes=meta.scopes,
            rate_limit_per_minute=meta.rate_limit_per_minute,
            created_at=meta.created_at,
            expires_at=meta.expires_at,
        )

    def validate_api_key(self, raw_key: str) -> ApiResult:
        """Convenience method to authenticate an API key."""
        inp = ApiInput(operation=ApiOperation.API_KEY_AUTHENTICATION, api_key=raw_key)
        return self.workflow.execute(inp)

    def rotate_api_key(self, key_id: str, grace_period_seconds: float = 0.0) -> ApiResult:
        """Convenience method to rotate an active API key."""
        inp = ApiInput(
            operation=ApiOperation.API_KEY_ROTATION,
            key_id=key_id,
            rotate_request=ApiKeyRotateRequest(
                key_id=key_id, grace_period_seconds=grace_period_seconds
            ),
        )
        return self.workflow.execute(inp)

    def revoke_api_key(self, key_id: str, reason: Optional[str] = None) -> ApiResult:
        """Convenience method to revoke an API key."""
        inp = ApiInput(
            operation=ApiOperation.API_KEY_REVOCATION,
            key_id=key_id,
            revoke_request=ApiKeyRevokeRequest(key_id=key_id, reason=reason),
        )
        return self.workflow.execute(inp)

    def check_permissions(self, key_id: str, scope: str) -> ApiResult:
        """Convenience method to check scoped authorization."""
        inp = ApiInput(
            operation=ApiOperation.SCOPED_PERMISSIONS,
            key_id=key_id,
            scope_to_check=scope,
        )
        return self.workflow.execute(inp)

    # -------------------------------------------------------------------------
    # Lifecycle & Health
    # -------------------------------------------------------------------------
    def health_check(self) -> HealthCheckResult:
        """Synchronously check operational health of API gateway and storage."""
        start_time = time.perf_counter()
        keys_count = len(self.registry.store.list_keys(include_revoked=True))
        logs_count = len(self.registry.gateway.get_audit_logs())

        details = {
            "initialized": self._initialized,
            "store_type": type(self.registry.store).__name__,
            "total_keys_count": keys_count,
            "audit_logs_count": logs_count,
            "gateway_ready": True,
            "version": "v1",
            "supported_capabilities": self.manifest.capabilities,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return HealthCheckResult(
            status=PluginHealthStatus.HEALTHY,
            details=details,
            latency_ms=latency_ms,
            error=None,
        )

    async def ahealth_check(self) -> HealthCheckResult:
        """Asynchronously check operational health."""
        return await asyncio.to_thread(self.health_check)

    def health(self) -> HealthCheckResult:
        """Standard plugin contract alias."""
        return self.health_check()

    def initialize(self) -> None:
        """Initialize plugin state."""
        self._initialized = True

    def shutdown(self) -> None:
        """Release plugin resources and reset state."""
        self._initialized = False

    # -------------------------------------------------------------------------
    # ASGI 3.0 Interface
    # -------------------------------------------------------------------------
    @property
    def asgi_app(self) -> Any:
        """Return the ASGI 3.0 application callable."""
        return self.registry.gateway


__all__ = ["ApiPlugin"]
