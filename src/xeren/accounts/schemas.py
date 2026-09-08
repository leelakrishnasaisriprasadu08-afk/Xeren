"""Pydantic schemas for user-authenticated external accounts and app activity logs."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AccountAuthStatus(str, Enum):
    AUTHENTICATED = "authenticated"
    PENDING = "pending"
    EXPIRED = "expired"
    DISCONNECTED = "disconnected"


class AccountPlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AppEventType(str, Enum):
    AUTH = "auth"
    SYNC = "sync"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    TOKEN_REFRESH = "token_refresh"


class UserConnectedAccount(BaseModel):
    """External app/AI connected directly as a user account."""
    app_id: str
    app_name: str
    icon: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    plan_tier: AccountPlanTier = AccountPlanTier.PRO
    auth_status: AccountAuthStatus = AccountAuthStatus.DISCONNECTED
    masked_token: Optional[str] = None
    connected_at: Optional[str] = None
    last_sync: Optional[str] = None
    category: str = "ai"  # ai, design, developer, productivity, media, local
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    requires_api_key: bool = True
    connection_type: str = "cloud_api"  # cloud_api, local_device, custom_url
    local_path: Optional[str] = None
    endpoint_url: Optional[str] = None
    is_custom: bool = False


class AppActivityLog(BaseModel):
    """Audit log entry for an action or authentication event under an app account."""
    log_id: str
    timestamp: str
    app_id: str
    app_name: str
    user_email: str
    event_type: AppEventType
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class AccountLoginRequest(BaseModel):
    """User account authentication request payload."""
    app_id: str
    user_email: str
    user_name: Optional[str] = None
    token_or_key: Optional[str] = None
    plan_tier: AccountPlanTier = AccountPlanTier.PRO
    local_path: Optional[str] = None
    endpoint_url: Optional[str] = None
    connection_type: Optional[str] = "cloud_api"


class AddLocalAppRequest(BaseModel):
    """Request payload to register a native local application from the user's device."""
    app_name: str
    category: str = "tools"
    local_path: Optional[str] = None
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    user_name: Optional[str] = None


class AddCustomAppRequest(BaseModel):
    """Request payload to register a custom application with URL, API key, and user details."""
    app_name: str
    category: str = "tools"
    connection_type: str = "cloud_api"  # cloud_api, custom_url, local_device
    endpoint_url: Optional[str] = None
    api_key_or_token: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    plan_tier: AccountPlanTier = AccountPlanTier.PRO
    local_path: Optional[str] = None
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
