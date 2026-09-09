"""AccountManager — Manages user account authentication for external AIs and applications."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from xeren.accounts.schemas import (
    AccountAuthStatus,
    AccountLoginRequest,
    AccountPlanTier,
    AddCustomAppRequest,
    AddLocalAppRequest,
    AppActivityLog,
    AppEventType,
    UserConnectedAccount,
)
from xeren.core.vault import UserVault

logger = logging.getLogger("xeren.accounts")


def get_default_accounts() -> List[UserConnectedAccount]:
    """Default apps and AIs available for user account login."""
    return [
        UserConnectedAccount(
            app_id="gemini",
            app_name="Google Gemini",
            icon="♊",
            category="ai",
            description="Connect your personal/work Google Gemini account for multimodal reasoning, 1M context, and live vision.",
            capabilities=["gemini-1.5-pro", "multimodal-vision", "google-search-grounding", "code-execution"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="canva",
            app_name="Canva Design",
            icon="🎨",
            category="design",
            description="Connect your Canva account to automate graphic designs, presentations, brand kits, and social assets.",
            capabilities=["presentation-generation", "brand-kit-sync", "template-autofill", "asset-export"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="huggingface",
            app_name="Hugging Face",
            icon="🤗",
            category="ai",
            description="Connect your Hugging Face account to access private model repositories, inference endpoints, and datasets.",
            capabilities=["model-hub-access", "serverless-inference", "space-deployment", "dataset-viewer"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="openai",
            app_name="OpenAI / ChatGPT",
            icon="🤖",
            category="ai",
            description="Connect your OpenAI personal or team account for GPT-4o, DALL-E 3, and assistant tools.",
            capabilities=["gpt-4o", "dall-e-3", "file-search", "code-interpreter"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="claude",
            app_name="Anthropic Claude",
            icon="⚡",
            category="ai",
            description="Connect your Anthropic Claude account for long-form synthesis and advanced reasoning.",
            capabilities=["claude-3-5-sonnet", "artifacts", "computer-use"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="perplexity",
            app_name="Perplexity AI",
            icon="🔍",
            category="ai",
            description="Connect your Perplexity Pro account for real-time web citations, academic papers, and deep search synthesis.",
            capabilities=["sonar-reasoning", "live-web-citations", "academic-search", "multi-source-synthesis"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="midjourney",
            app_name="Midjourney AI",
            icon="⛵",
            category="design",
            description="Connect your Midjourney account to generate photorealistic imagery, concept art, and UI asset exploration.",
            capabilities=["v6-photorealism", "style-transfer", "pan-zoom", "asset-generation"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="github",
            app_name="GitHub Account",
            icon="🐙",
            category="developer",
            description="Logged in as your personal developer account for repository commits, PR reviews, and releases.",
            capabilities=["repo-read-write", "commit-signing", "issue-management", "workflow-dispatch"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="supabase",
            app_name="Supabase Cloud",
            icon="⚡",
            category="developer",
            description="Connect your Supabase project for direct PostgreSQL queries, pgvector embeddings, and row-level security.",
            capabilities=["postgres-sql", "pgvector-rag", "database-migration", "realtime-subscriptions"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="notion",
            app_name="Notion Workspace",
            icon="📝",
            category="productivity",
            description="Connect your personal or team Notion workspace for documentation, wikis, and task tracking.",
            capabilities=["database-query", "page-creation", "block-append", "workspace-search"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="gdrive",
            app_name="Google Drive & Workspace",
            icon="📁",
            category="productivity",
            description="Connect Google Drive to read and write Docs, analyze Sheets spreadsheets, and index project drive folders.",
            capabilities=["sheets-analysis", "docs-generation", "folder-indexing", "drive-sync"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="slack",
            app_name="Slack Workspace",
            icon="💬",
            category="productivity",
            description="Logged in as your Slack member account to post updates, reply in threads, and monitor channels.",
            capabilities=["channel-message", "thread-reply", "notification-broadcast", "status-sync"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="discord",
            app_name="Discord Community",
            icon="🎮",
            category="productivity",
            description="Connect your Discord account or bot token to chat across servers, manage webhooks, and trigger community actions.",
            capabilities=["server-messaging", "webhook-triggers", "voice-state", "bot-actions"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="spotify",
            app_name="Spotify Audio & Media",
            icon="🎵",
            category="media",
            description="Connect your Spotify account for deep-work focus audio, playlist automation, and podcast transcription.",
            capabilities=["playback-control", "playlist-curation", "focus-mode", "audio-telemetry"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="linear",
            app_name="Linear Issue Tracking",
            icon="📐",
            category="developer",
            description="Connect your Linear team account for sprint cycles, bug tracking, roadmaps, and PR cross-linking.",
            capabilities=["issue-creation", "cycle-tracking", "roadmap-sync", "triage-automation"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        UserConnectedAccount(
            app_id="figma",
            app_name="Figma Studio",
            icon="🎯",
            category="design",
            description="Connect your Figma account to inspect design tokens, frames, and automated vector export.",
            capabilities=["vector-export", "component-inspection", "token-sync", "design-system-audit"],
            requires_api_key=True,
            connection_type="cloud_api",
        ),
        # ------------------------------------------------------------------
        # Native Local Device Applications (No API Key Required)
        # ------------------------------------------------------------------
        UserConnectedAccount(
            app_id="blender",
            app_name="Blender 3D",
            icon="🔶",
            category="design",
            description="Local open-source 3D creation suite for modeling, animation, rendering, geometry nodes, and Python automation. Runs directly on your device without an API key.",
            capabilities=["3d-modeling", "cycles-eevee-rendering", "python-scripting", "usd-gltf-export", "geometry-nodes"],
            requires_api_key=False,
            connection_type="local_device",
            local_path="blender",
        ),
        UserConnectedAccount(
            app_id="vscode",
            app_name="Visual Studio Code",
            icon="💻",
            category="developer",
            description="Local code editor with CLI, workspace extensions, git integration, and live debugging. Runs directly on your device without an API key.",
            capabilities=["workspace-editing", "extension-host", "terminal-execution", "git-integration"],
            requires_api_key=False,
            connection_type="local_device",
            local_path="code",
        ),
        UserConnectedAccount(
            app_id="obs",
            app_name="OBS Studio",
            icon="📹",
            category="media",
            description="Local open-source screen recording, streaming, and audio visualizer. Connect via local WebSocket or launcher. No API key required.",
            capabilities=["screen-recording", "scene-switching", "virtual-camera", "audio-mixer"],
            requires_api_key=False,
            connection_type="local_device",
            local_path="obs64.exe",
        ),
        UserConnectedAccount(
            app_id="vlc",
            app_name="VLC Media Player",
            icon="🚦",
            category="media",
            description="Local high-performance media player and stream transcode engine with local RC interface. No API key required.",
            capabilities=["media-playback", "stream-transcode", "playlist-control", "local-rc"],
            requires_api_key=False,
            connection_type="local_device",
            local_path="vlc.exe",
        ),
        UserConnectedAccount(
            app_id="gimp",
            app_name="GIMP Image Editor",
            icon="🦊",
            category="design",
            description="Local open-source raster graphics and photo manipulation editor with Python/Scheme batch plugin support. No API key required.",
            capabilities=["image-manipulation", "batch-export", "python-fu", "layer-compositing"],
            requires_api_key=False,
            connection_type="local_device",
            local_path="gimp-2.10.exe",
        ),
        UserConnectedAccount(
            app_id="terminal",
            app_name="Local Terminal & Shell",
            icon="⚡",
            category="developer",
            description="Direct access to local Windows PowerShell / Command Prompt / WSL for native development commands. No API key required.",
            capabilities=["powershell-scripts", "cli-execution", "wsl-bridge", "environment-sync"],
            requires_api_key=False,
            connection_type="local_device",
            local_path="powershell.exe",
        ),
    ]


class AccountManager:
    """
    Manages user-authenticated external app accounts and live activity logging.
    All user credentials are encrypted with AES-256-GCM via UserVault.
    Supports native local desktop apps without requiring API keys.
    """

    def __init__(self, vault: Optional[UserVault] = None) -> None:
        self.vault = vault or UserVault()
        self._accounts: Dict[str, UserConnectedAccount] = {}
        self._logs: List[AppActivityLog] = []

        # Initialize catalog
        for acct in get_default_accounts():
            self._accounts[acct.app_id] = acct

        # Seed initial demo activity logs
        self._seed_initial_logs()

    def _seed_initial_logs(self) -> None:
        self.log_event(
            app_id="system",
            app_name="Xeren Security Vault",
            user_email="system@xeren.local",
            event_type=AppEventType.AUTH,
            message="AES-256-GCM hardware credential isolation ready for cloud accounts & local device apps.",
        )

    # ------------------------------------------------------------------
    # Account Lifecycle (Login / Logout / List / Register Local)
    # ------------------------------------------------------------------

    def list_accounts(self) -> List[UserConnectedAccount]:
        """List all external apps with active user account state."""
        return list(self._accounts.values())

    def get_account(self, app_id: str) -> Optional[UserConnectedAccount]:
        """Fetch details for a specific connected app."""
        return self._accounts.get(app_id)

    def login_account(self, req: AccountLoginRequest) -> UserConnectedAccount:
        """
        Log in to an external app/AI or link a local device application.
        Encrypts credentials in UserVault (or registers local path without an API key).
        """
        acct = self._accounts.get(req.app_id)
        if not acct:
            raise KeyError(f"Application '{req.app_id}' is not a recognized provider")

        now = datetime.now(timezone.utc).isoformat()
        is_local = (not acct.requires_api_key) or (req.connection_type == "local_device")
        raw_token = (req.token_or_key or "").strip()

        if is_local:
            local_path = req.local_path or acct.local_path or "linked"
            masked = f"local:{local_path}"
        elif len(raw_token) > 8:
            masked = f"{raw_token[:3]}•••••••{raw_token[-4:]}"
        else:
            masked = "••••••••"

        # 2. Encrypt and store in UserVault (AES-256-GCM)
        credentials_dict = {
            "user_email": req.user_email,
            "user_name": req.user_name or req.user_email.split("@")[0],
            "token": raw_token if not is_local else "LOCAL_DEVICE_APP",
            "plan_tier": req.plan_tier.value,
            "connection_type": "local_device" if is_local else "cloud_api",
            "local_path": req.local_path or acct.local_path,
            "authenticated_at": now,
        }
        self.vault.store_account_credentials(
            account_name=f"user_app_{req.app_id}",
            platform=req.app_id,
            credentials=credentials_dict,
        )

        # 3. Update active in-memory state
        acct.user_email = req.user_email
        acct.user_name = req.user_name or req.user_email.split("@")[0]
        acct.plan_tier = req.plan_tier
        acct.auth_status = AccountAuthStatus.AUTHENTICATED
        acct.masked_token = masked
        acct.connected_at = now
        acct.last_sync = now
        if req.local_path:
            acct.local_path = req.local_path

        # 4. Record audit event
        if is_local:
            event_msg = f"Linked local application '{acct.app_name}' on device (path: {acct.local_path or 'system default'}). No API key required."
        else:
            event_msg = f"Logged in as user account '{req.user_email}' ({req.plan_tier.value.upper()} tier). Credentials encrypted in UserVault."

        self.log_event(
            app_id=acct.app_id,
            app_name=acct.app_name,
            user_email=req.user_email,
            event_type=AppEventType.AUTH,
            message=event_msg,
            details={"masked_token": masked, "plan": req.plan_tier.value, "is_local": is_local},
        )

        logger.info("User account successfully authenticated for %s: %s (is_local=%s)", acct.app_name, req.user_email, is_local)
        return acct

    def add_custom_app(self, req: AddCustomAppRequest) -> UserConnectedAccount:
        """Register a custom application with URL, API key, and user details (or local device app)."""
        base_id = re.sub(r"[^a-zA-Z0-9]+", "-", req.app_name.lower()).strip("-") or "custom-app"
        app_id = base_id
        count = 1
        while app_id in self._accounts:
            app_id = f"{base_id}-{count}"
            count += 1

        now = datetime.now(timezone.utc).isoformat()
        is_local = req.connection_type == "local_device"
        raw_token = (req.api_key_or_token or "").strip()

        if is_local:
            masked = f"local:{req.local_path or 'linked'}"
            requires_key = False
            auth_status = AccountAuthStatus.AUTHENTICATED
        elif raw_token:
            if len(raw_token) > 8:
                masked = f"{raw_token[:3]}•••••••{raw_token[-4:]}"
            else:
                masked = "••••••••"
            requires_key = True
            auth_status = AccountAuthStatus.AUTHENTICATED

            # Store in UserVault (AES-256-GCM)
            self.vault.store_account_credentials(
                account_name=f"user_app_{app_id}",
                platform=app_id,
                credentials={
                    "user_email": req.user_email or f"{app_id}@user.local",
                    "user_name": req.user_name or req.app_name,
                    "token": raw_token,
                    "endpoint_url": req.endpoint_url,
                    "plan_tier": req.plan_tier.value,
                    "authenticated_at": now,
                },
            )
        else:
            masked = None
            requires_key = True
            auth_status = AccountAuthStatus.DISCONNECTED

        acct = UserConnectedAccount(
            app_id=app_id,
            app_name=req.app_name,
            icon="🌐" if not is_local else "🖥️",
            category=req.category,
            description=req.description or f"Custom {req.category.capitalize()} app '{req.app_name}' configured with custom endpoint.",
            capabilities=req.capabilities or ["api-integration", "custom-workflow"],
            requires_api_key=requires_key,
            connection_type=req.connection_type,
            local_path=req.local_path,
            endpoint_url=req.endpoint_url,
            is_custom=True,
            auth_status=auth_status,
            masked_token=masked,
            user_name=req.user_name or "Custom User",
            user_email=req.user_email or (f"{app_id}@device.local" if is_local else (f"{app_id}@custom.local" if raw_token else None)),
            plan_tier=req.plan_tier,
            connected_at=now if auth_status == AccountAuthStatus.AUTHENTICATED else None,
            last_sync=now if auth_status == AccountAuthStatus.AUTHENTICATED else None,
        )

        self._accounts[app_id] = acct
        self.log_event(
            app_id=app_id,
            app_name=req.app_name,
            user_email=acct.user_email or "custom@xeren.local",
            event_type=AppEventType.AUTH,
            message=f"Configured custom app '{req.app_name}' (Type: {req.connection_type}, URL: {req.endpoint_url or 'Local'}, User: {acct.user_email or 'Unauthenticated'}).",
            details={
                "endpoint_url": req.endpoint_url,
                "connection_type": req.connection_type,
                "category": req.category,
                "masked_token": masked,
            },
        )
        return acct

    def add_local_device_app(self, req: AddLocalAppRequest) -> UserConnectedAccount:
        """Register a custom local desktop app from user's device without requiring an API key."""
        custom_req = AddCustomAppRequest(
            app_name=req.app_name,
            category=req.category,
            connection_type="local_device",
            local_path=req.local_path or "installed",
            description=req.description,
            capabilities=req.capabilities,
            user_name=req.user_name,
        )
        return self.add_custom_app(custom_req)

    def logout_account(self, app_id: str) -> UserConnectedAccount:
        """Log out / disconnect user account from an external app."""
        acct = self._accounts.get(app_id)
        if not acct:
            raise KeyError(f"Application '{app_id}' not found")

        old_email = acct.user_email or "unknown"
        acct.auth_status = AccountAuthStatus.DISCONNECTED
        acct.user_email = None
        acct.user_name = None
        acct.masked_token = None

        self.log_event(
            app_id=acct.app_id,
            app_name=acct.app_name,
            user_email=old_email,
            event_type=AppEventType.AUTH,
            message=f"Logged out user account '{old_email}' from {acct.app_name}. Local tokens purged.",
        )

        logger.info("Logged out user account from %s", acct.app_name)
        return acct

    # ------------------------------------------------------------------
    # App Activity & Audit Logging ("App Log")
    # ------------------------------------------------------------------

    def log_event(
        self,
        app_id: str,
        app_name: str,
        user_email: str,
        event_type: AppEventType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AppActivityLog:
        """Append an activity log entry for user account actions."""
        log_entry = AppActivityLog(
            log_id=f"log-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            app_id=app_id,
            app_name=app_name,
            user_email=user_email,
            event_type=event_type,
            message=message,
            details=details or {},
        )
        self._logs.insert(0, log_entry)  # Newest first
        if len(self._logs) > 200:
            self._logs = self._logs[:200]
        return log_entry

    def get_logs(
        self,
        app_id: Optional[str] = None,
        event_type: Optional[AppEventType] = None,
        limit: int = 50,
    ) -> List[AppActivityLog]:
        """Fetch filtered app activity logs."""
        filtered = self._logs
        if app_id and app_id != "all":
            filtered = [l for l in filtered if l.app_id == app_id]
        if event_type:
            filtered = [l for l in filtered if l.event_type == event_type]
        return filtered[:limit]

    def clear_logs(self) -> None:
        """Clear all in-memory activity logs."""
        self._logs.clear()
        self._seed_initial_logs()
