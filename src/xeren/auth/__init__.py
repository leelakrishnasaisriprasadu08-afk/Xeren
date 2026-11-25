"""Authentication & User Identity Module for Xeren."""
from xeren.auth.schemas import (
    AuthMethod,
    UserProfile,
    SocialAuthRequest,
    PasskeyRegisterRequest,
    PasskeyAuthRequest,
    OTPRequest,
    OTPVerifyRequest,
    ProfileUpdateRequest,
)
from xeren.auth.manager import AuthManager

__all__ = [
    "AuthMethod",
    "UserProfile",
    "SocialAuthRequest",
    "PasskeyRegisterRequest",
    "PasskeyAuthRequest",
    "OTPRequest",
    "OTPVerifyRequest",
    "ProfileUpdateRequest",
    "AuthManager",
]
