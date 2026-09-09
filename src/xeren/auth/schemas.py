"""Pydantic schemas for Multi-Method Authentication and User Identity."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    FACEBOOK = "facebook"
    PASSKEY = "passkey"
    EMAIL_OTP = "email_otp"
    PHONE_OTP = "phone_otp"


class PasskeyCredential(BaseModel):
    credential_id: str
    device_name: str = "Biometric / Security Key"
    public_key: str
    created_at: str
    last_used_at: str


class UserProfile(BaseModel):
    user_id: str
    handle: str = Field(description="Unique Xeren handle, e.g. @alex")
    display_name: str
    email: str
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    plan_tier: str = "Pro Studio"
    linked_methods: List[AuthMethod] = Field(default_factory=list)
    passkeys: List[PasskeyCredential] = Field(default_factory=list)
    active_project_id: Optional[str] = None
    created_at: str
    last_login_at: str


class SocialAuthRequest(BaseModel):
    provider: str = Field(description="google, github, or facebook")
    token_or_code: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class PasskeyRegisterRequest(BaseModel):
    device_name: str = "Windows Hello / Touch ID / FIDO2 Key"
    credential_id: str
    public_key: str


class PasskeyAuthRequest(BaseModel):
    credential_id: str
    client_data_json: Optional[str] = None
    signature: Optional[str] = None


class OTPRequest(BaseModel):
    target: str = Field(description="Email address or international phone number")
    method: str = Field(default="email", description="'email' or 'phone'")


class OTPVerifyRequest(BaseModel):
    target: str
    code: str
    method: str = "email"


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    handle: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
