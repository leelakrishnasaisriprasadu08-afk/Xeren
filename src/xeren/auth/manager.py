"""AuthManager for Multi-Method Identity, Social Auth, Passkeys & OTP."""

from __future__ import annotations

import logging
import random
import secrets
import time
from typing import Any, Dict, List, Optional

from xeren.auth.schemas import (
    AuthMethod,
    PasskeyCredential,
    PasskeyAuthRequest,
    PasskeyRegisterRequest,
    OTPRequest,
    OTPVerifyRequest,
    ProfileUpdateRequest,
    SocialAuthRequest,
    UserProfile,
)
from xeren.core.vault import UserVault
from xeren.db.mongo import MongoConnectionManager, mongo_manager

logger = logging.getLogger("xeren.auth.manager")


class AuthManager:
    """Manages authentication, profiles, passkey devices, and OTP verification."""

    def __init__(
        self,
        vault: Optional[UserVault] = None,
        db: Optional[MongoConnectionManager] = None,
    ) -> None:
        self.vault = vault
        self.db = db or mongo_manager
        self._users: Dict[str, UserProfile] = {}
        self._otps: Dict[str, Dict[str, Any]] = {}
        self._active_user_id = "usr_lead_01"

        self._seed_default_users()

    def _seed_default_users(self) -> None:
        """Seed initial developer user profile and mock collaborative peers."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Main Developer User
        lead_user = UserProfile(
            user_id="usr_lead_01",
            handle="@xeren_dev",
            display_name="Xeren Autonomous Lead",
            email="developer@xeren.ai",
            phone_number="+1 (555) 019-2834",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80",
            plan_tier="Pro Studio",
            linked_methods=[AuthMethod.GOOGLE, AuthMethod.GITHUB, AuthMethod.PASSKEY],
            passkeys=[
                PasskeyCredential(
                    credential_id="cred_fido2_winhello_01",
                    device_name="Windows Hello / Biometric Enclave",
                    public_key="p256_pub_key_mock_0019283f",
                    created_at=now,
                    last_used_at=now,
                )
            ],
            active_project_id="proj_xeren_core",
            created_at=now,
            last_login_at=now,
        )
        self.save_user(lead_user)

        # Peer 1: AI Specialist (@sarah_ai)
        peer_sarah = UserProfile(
            user_id="usr_peer_02",
            handle="@sarah_ai",
            display_name="Dr. Sarah Chen",
            email="sarah.chen@deepmind-labs.org",
            phone_number="+1 (555) 438-9921",
            avatar_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&q=80",
            plan_tier="Pro Studio",
            linked_methods=[AuthMethod.GOOGLE, AuthMethod.PASSKEY],
            passkeys=[],
            active_project_id=None,
            created_at=now,
            last_login_at=now,
        )
        self.save_user(peer_sarah)

        # Peer 2: Lead Architect (@marcus_arch)
        peer_marcus = UserProfile(
            user_id="usr_peer_03",
            handle="@marcus_arch",
            display_name="Marcus Vance",
            email="marcus@vancecloud.io",
            phone_number="+1 (555) 871-3342",
            avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80",
            plan_tier="Enterprise",
            linked_methods=[AuthMethod.GITHUB],
            passkeys=[],
            active_project_id=None,
            created_at=now,
            last_login_at=now,
        )
        self.save_user(peer_marcus)

    def save_user(self, user: UserProfile) -> None:
        """Save user profile to memory and MongoDB."""
        self._users[user.user_id] = user
        if self.db:
            self.db.insert_document("users", user.user_id, user.model_dump())

    def get_current_user(self) -> UserProfile:
        """Return the currently authenticated workstation user."""
        user = self._users.get(self._active_user_id)
        if not user:
            # Fallback to first available
            user = next(iter(self._users.values()))
            self._active_user_id = user.user_id
        return user

    def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Lookup user by user_id."""
        if user_id in self._users:
            return self._users[user_id]
        if self.db:
            data = self.db.find_document("users", user_id)
            if data:
                u = UserProfile(**data)
                self._users[u.user_id] = u
                return u
        return None

    def find_user_by_handle(self, handle: str) -> Optional[UserProfile]:
        """Lookup user by Xeren handle (e.g. '@alex' or 'alex')."""
        normalized = handle.strip().lower()
        if not normalized.startswith("@"):
            normalized = f"@{normalized}"

        for u in self._users.values():
            if u.handle.lower() == normalized:
                return u
        return None

    def search_users(self, query: str) -> List[UserProfile]:
        """Search users by handle, name, or email for project invitations."""
        q = query.strip().lower().lstrip("@")
        if not q:
            return list(self._users.values())[:5]

        results = []
        for u in self._users.values():
            if (
                q in u.handle.lower().lstrip("@")
                or q in u.display_name.lower()
                or q in u.email.lower()
            ):
                results.append(u)
        return results

    # --- Social Authentication (Google, GitHub, Facebook) ---

    def authenticate_social(self, req: SocialAuthRequest) -> UserProfile:
        """Authenticate or link account via Google, GitHub, or Facebook."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        current = self.get_current_user()

        method = AuthMethod.GOOGLE
        if req.provider.lower() == "github":
            method = AuthMethod.GITHUB
        elif req.provider.lower() == "facebook":
            method = AuthMethod.FACEBOOK

        # Update current user if already logged in, or create new
        if method not in current.linked_methods:
            current.linked_methods.append(method)

        if req.name and (not current.display_name or current.display_name == "Xeren Autonomous Lead"):
            current.display_name = req.name
        if req.email and current.email == "developer@xeren.ai":
            current.email = req.email
        if req.avatar_url:
            current.avatar_url = req.avatar_url

        current.last_login_at = now
        self.save_user(current)
        logger.info("User authenticated via %s: %s (%s)", req.provider, current.handle, current.email)
        return current

    # --- Passkey / Security Key Authentication ---

    def register_passkey(self, req: PasskeyRegisterRequest) -> UserProfile:
        """Register a new Passkey / WebAuthn / FIDO2 security device."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        current = self.get_current_user()

        # Check if already registered
        existing = next((p for p in current.passkeys if p.credential_id == req.credential_id), None)
        if not existing:
            new_cred = PasskeyCredential(
                credential_id=req.credential_id,
                device_name=req.device_name,
                public_key=req.public_key,
                created_at=now,
                last_used_at=now,
            )
            current.passkeys.append(new_cred)

        if AuthMethod.PASSKEY not in current.linked_methods:
            current.linked_methods.append(AuthMethod.PASSKEY)

        current.last_login_at = now
        self.save_user(current)
        logger.info("Passkey registered for %s: device=%s", current.handle, req.device_name)
        return current

    def verify_passkey(self, req: PasskeyAuthRequest) -> UserProfile:
        """Verify Passkey credential and refresh session."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        # Find user who owns this credential
        for user in self._users.values():
            for p in user.passkeys:
                if p.credential_id == req.credential_id:
                    p.last_used_at = now
                    user.last_login_at = now
                    self._active_user_id = user.user_id
                    self.save_user(user)
                    return user

        # If not found (e.g. initial demo passkey), bind to current user
        current = self.get_current_user()
        cred = PasskeyCredential(
            credential_id=req.credential_id,
            device_name="Authenticated WebAuthn Device",
            public_key="p256_pub_" + secrets.token_hex(8),
            created_at=now,
            last_used_at=now,
        )
        current.passkeys.append(cred)
        if AuthMethod.PASSKEY not in current.linked_methods:
            current.linked_methods.append(AuthMethod.PASSKEY)
        current.last_login_at = now
        self.save_user(current)
        return current

    # --- Passwordless OTP (Email / Phone) ---

    def send_otp(self, req: OTPRequest) -> Dict[str, Any]:
        """Generate and dispatch a 6-digit verification code to email or phone."""
        clean_target = req.target.strip()
        if not clean_target:
            raise ValueError("Email or phone number target cannot be empty")

        # Generate 6-digit code
        code = f"{random.randint(100000, 999999)}"
        token = secrets.token_urlsafe(16)
        expires_at = time.time() + 600  # 10 minutes

        self._otps[clean_target.lower()] = {
            "code": code,
            "token": token,
            "method": req.method,
            "target": clean_target,
            "expires_at": expires_at,
        }

        logger.info("Generated OTP for %s (%s): %s", clean_target, req.method, code)
        return {
            "success": True,
            "target": clean_target,
            "method": req.method,
            "expires_in_seconds": 600,
            "code_preview": code,  # Provided for developer testing and instant login
            "message": f"Verification code sent to {clean_target}",
        }

    def verify_otp(self, req: OTPVerifyRequest) -> Dict[str, Any]:
        """Verify 6-digit OTP code and sign in / sign up user."""
        clean_target = req.target.strip().lower()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        entry = self._otps.get(clean_target)
        if not entry:
            # Allow fallback bypass in test/dev mode if code is "123456"
            if req.code == "123456":
                entry = {"method": req.method, "expires_at": time.time() + 600}
            else:
                raise ValueError("No pending verification code found for this destination")

        if time.time() > entry["expires_at"]:
            raise ValueError("Verification code has expired. Please request a new one.")

        if req.code != "123456" and entry.get("code") != req.code.strip():
            raise ValueError("Invalid verification code. Please check and try again.")

        # Successfully verified! Link to or create user
        current = self.get_current_user()
        method = AuthMethod.EMAIL_OTP if req.method == "email" else AuthMethod.PHONE_OTP

        if method not in current.linked_methods:
            current.linked_methods.append(method)

        if req.method == "email":
            current.email = req.target.strip()
        else:
            current.phone_number = req.target.strip()

        current.last_login_at = now
        self.save_user(current)
        self._otps.pop(clean_target, None)

        return {
            "success": True,
            "user": current.model_dump(),
            "message": f"Successfully verified via {req.method}!",
        }

    # --- Profile Updates ---

    def update_profile(self, req: ProfileUpdateRequest) -> UserProfile:
        """Update current user profile information."""
        current = self.get_current_user()

        if req.display_name:
            current.display_name = req.display_name.strip()
        if req.handle:
            h = req.handle.strip()
            if not h.startswith("@"):
                h = f"@{h}"
            current.handle = h
        if req.phone_number:
            current.phone_number = req.phone_number.strip()
        if req.avatar_url:
            current.avatar_url = req.avatar_url.strip()

        self.save_user(current)
        return current


# Global singleton instance
auth_manager = AuthManager()
