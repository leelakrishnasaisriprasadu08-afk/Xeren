"""Tool registry aggregating authorities and adapters for the Xeren API Plugin."""

from typing import Any, Callable, Optional

from xeren.plugins.api.tools.auth import ApiKeyManagerTool
from xeren.plugins.api.tools.gateway import ApiGatewayTool
from xeren.plugins.api.tools.limiter import BaseRateLimiter, SlidingWindowRateLimiter
from xeren.plugins.api.tools.redactor import ApiSecretRedactorTool
from xeren.plugins.api.tools.store import BaseApiKeyStore, InMemoryApiKeyStore
from xeren.plugins.api.tools.validator import RequestValidatorTool
from xeren.plugins.manager import PluginManager


class ApiToolRegistry:
    """Registry coordinating API authentication, persistence, routing, and validation tools."""

    def __init__(
        self,
        store: Optional[BaseApiKeyStore] = None,
        auth_manager: Optional[ApiKeyManagerTool] = None,
        validator: Optional[RequestValidatorTool] = None,
        rate_limiter: Optional[BaseRateLimiter] = None,
        redactor: Optional[ApiSecretRedactorTool] = None,
        gateway: Optional[ApiGatewayTool] = None,
        plugin_manager: Optional[PluginManager] = None,
    ) -> None:
        self.store = store or InMemoryApiKeyStore()
        self.auth_manager = auth_manager or ApiKeyManagerTool(store=self.store)
        self.validator = validator or RequestValidatorTool()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()
        self.redactor = redactor or ApiSecretRedactorTool()
        self.gateway = gateway or ApiGatewayTool(
            auth_manager=self.auth_manager,
            validator=self.validator,
            rate_limiter=self.rate_limiter,
            redactor=self.redactor,
        )
        self.plugin_manager = plugin_manager
        self.core: Optional[Any] = None

    def set_plugin_manager(self, manager: PluginManager) -> None:
        """Attach PluginManager reference and wire dispatcher."""
        self.plugin_manager = manager

    def set_core(self, core: Any) -> None:
        """Attach XerenCore reference and wire gateway dispatcher."""
        self.core = core
        if hasattr(core, "execute_plugin"):
            def core_dispatcher(plugin_name: str, payload: Any) -> Any:
                if plugin_name == "health":
                    return core.check_health()
                res = core.execute_plugin(plugin_name, payload)
                if not res.success:
                    raise RuntimeError(res.error or f"Failed execution in '{plugin_name}'.")
                return res.output

            self.gateway.set_core_dispatcher(core_dispatcher)

    def set_custom_dispatcher(self, dispatcher: Callable[[str, Any], Any]) -> None:
        """Attach a mock or custom dispatcher for deterministic testing."""
        self.gateway.set_core_dispatcher(dispatcher)


__all__ = ["ApiToolRegistry"]
