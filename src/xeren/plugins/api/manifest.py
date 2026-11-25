"""Manifest metadata specification for the Xeren API / Communication Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

API_PLUGIN_MANIFEST = PluginManifest(
    name="api",
    version="0.1.0",
    description=(
        "Exposes secure client-facing API interfaces for Xeren Core with independent "
        "credentials, HMAC-SHA256 authentication, scoped authorization, request size "
        "ceilings, rate limiting, secret redaction, and /v1 standardized responses."
    ),
    capabilities=[
        PluginCapability.API_REQUEST.value,
        PluginCapability.API_RESPONSE.value,
        PluginCapability.API_KEY_AUTHENTICATION.value,
        PluginCapability.API_KEY_ROTATION.value,
        PluginCapability.API_KEY_REVOCATION.value,
        PluginCapability.SCOPED_PERMISSIONS.value,
        PluginCapability.REQUEST_VALIDATION.value,
        PluginCapability.RATE_LIMITING.value,
        PluginCapability.REQUEST_LOGGING.value,
        PluginCapability.HEALTH_STATUS.value,
    ],
    input_schema_name="ApiInput",
    output_schema_name="ApiResult",
    author="Xeren Team",
    metadata={
        "category": "communication_gateway",
        "version_tag": "v1",
        "auth_scheme": "Bearer/X-API-Key",
        "database_independent": True,
        "default_rate_limit_per_minute": 60,
        "max_request_bytes": 2 * 1024 * 1024,
    },
)

__all__ = ["API_PLUGIN_MANIFEST"]
