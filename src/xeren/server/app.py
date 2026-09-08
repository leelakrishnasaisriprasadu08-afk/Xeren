"""FastAPI Bridge Server for Xeren Desktop GUI Command Center."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from xeren.core.dispatcher import XerenDispatcher
from xeren.core.session import XerenSession
from xeren.core.vault import UserVault
from xeren.security.schemas import DataSensitivityTier
from xeren.automation.manager import MultiWorkspaceManager
from xeren.automation.schemas import PlatformType
from xeren.plugins.research.tools.strawberry_planner import StrawberryQueryPlanner
from xeren.plugins.research.tools.claim_verifier import ClaimVerifier
from xeren.voice.manager import VoiceSessionManager
from xeren.channels.manager import ChannelsManager
from xeren.mcp.manager import MCPManager
from xeren.mcp.schemas import MCPServerConfig, CrossAppPipeline
from xeren.mcp.presets import get_default_mcp_presets
from xeren.accounts.manager import AccountManager
from xeren.accounts.schemas import AccountLoginRequest, AddCustomAppRequest, AddLocalAppRequest, AppEventType
from xeren.db.mongo import mongo_manager
from xeren.auth.manager import auth_manager
from xeren.auth.schemas import (
    OTPRequest,
    OTPVerifyRequest,
    PasskeyAuthRequest,
    PasskeyRegisterRequest,
    ProfileUpdateRequest,
    SocialAuthRequest,
)
from xeren.projects.manager import project_manager
from xeren.projects.schemas import (
    CoachChatRequest,
    MemberRoleUpdateRequest,
    ProjectCreateRequest,
    ProjectInviteRequest,
    ProjectJoinCodeRequest,
    ProjectSpecUpdateRequest,
    WorkstationHeartbeatRequest,
)
from xeren.models.improvement.engine import llm_improvement_engine
from xeren.models.improvement.schemas import (
    AnalyzeImprovementsRequest,
    RecordObservationRequest,
    ToggleDirectiveRequest,
)

logger = logging.getLogger("xeren.server")

app = FastAPI(title="Xeren Local Intelligence Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global runtime services
vault = UserVault()
session = XerenSession(vault=vault)
dispatcher = XerenDispatcher(session=session)
workspace_mgr = MultiWorkspaceManager(security_gate=session.gate)
strawberry_planner = StrawberryQueryPlanner()
claim_verifier = ClaimVerifier()
voice_mgr = VoiceSessionManager(dispatcher=dispatcher)
channels_mgr = ChannelsManager(vault=vault)
mcp_mgr = MCPManager(load_defaults=True)
account_mgr = AccountManager(vault=vault)


# Request/Response models
class DispatchRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


class UnlockRequest(BaseModel):
    tier: str
    pin: str


class OrderCreateRequest(BaseModel):
    order_id: str
    platform: str
    client_name: str
    amount_usd: float
    brief_prompt: str
    project_type: str = "website"


class StrawberryResearchRequest(BaseModel):
    topic: str
    depth: str = "deep"


class MCPToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


class MCPToggleRequest(BaseModel):
    enabled: Optional[bool] = None


class MCPPipelineExecuteRequest(BaseModel):
    pipeline_id: Optional[str] = None
    custom_pipeline: Optional[CrossAppPipeline] = None


@app.get("/api/health")
def health():
    return {"status": "online", "session_id": session.session_id, "user_id": session.user_id}


@app.post("/api/dispatch")
def dispatch_query(req: DispatchRequest):
    resp = dispatcher.dispatch(req.query, context=req.context)
    return {
        "success": resp.success,
        "plugin": resp.plugin_name,
        "intent": resp.intent.action,
        "confidence": resp.intent.confidence,
        "data": resp.data,
        "error": resp.error,
    }


@app.get("/api/security/tiers")
def get_security_status():
    return {
        "liberal": {"status": "unlocked", "encryption": "none"},
        "sensitive": {
            "status": "unlocked" if session.is_tier_accessible(DataSensitivityTier.SENSITIVE) else "locked",
            "encryption": "AES-256-CBC",
            "timeout_minutes": 30,
        },
        "more_sensitive": {
            "status": "unlocked" if session.is_tier_accessible(DataSensitivityTier.MORE_SENSITIVE) else "locked",
            "encryption": "AES-256-GCM",
            "timeout_minutes": 10,
        },
        "granted_directories": vault.get_all_granted_directories(),
    }


@app.post("/api/security/unlock")
def unlock_tier(req: UnlockRequest):
    try:
        tier = DataSensitivityTier(req.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    success = session.unlock_tier_with_pin(tier, req.pin)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {"success": True, "tier": req.tier, "unlocked": True}


@app.get("/api/workspaces")
def list_workspaces():
    orders = workspace_mgr.list_all_active_orders()
    return {
        "active_workspace": session.active_workspace_type,
        "orders": [
            {
                "order_id": o.order_id,
                "platform": o.platform.value,
                "client_name": o.client_name,
                "amount_usd": o.amount_usd,
                "status": o.status.value,
                "workspace_directory": o.workspace_directory,
                "brief": o.brief.__dict__ if o.brief else None,
            }
            for o in orders
        ]
    }


@app.post("/api/workspaces/orders")
def create_order(req: OrderCreateRequest):
    try:
        platform = PlatformType(req.platform.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    order = workspace_mgr.register_incoming_order(
        order_id=req.order_id,
        platform=platform,
        client_name=req.client_name,
        amount_usd=req.amount_usd,
        brief_prompt=req.brief_prompt,
        project_type=req.project_type,
    )
    return {"success": True, "order_id": order.order_id, "status": order.status.value}


@app.post("/api/workspaces/orders/{order_id}/execute")
def execute_order(order_id: str):
    try:
        package = workspace_mgr.execute_order_pipeline(order_id)
        return {"success": True, "package": package.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/research/strawberry")
def strawberry_research(req: StrawberryResearchRequest):
    plan = strawberry_planner.create_plan(req.topic, depth=req.depth)
    return {
        "topic": plan.original_topic,
        "safe_search_enforced": plan.safe_search_enforced,
        "angles": [a.__dict__ for a in plan.angles],
    }


@app.get("/api/channels")
def get_channels():
    return {
        "telegram": {"type": "telegram", "active": True},
        "discord": {"type": "discord", "active": True},
        "whatsapp": {"type": "whatsapp", "active": True},
    }


# ======================================================================
# MODEL CONTEXT PROTOCOL (MCP) & CROSS-APP INTEROPERABILITY ENDPOINTS
# ======================================================================

@app.get("/api/mcp/servers")
def get_mcp_servers():
    """List all registered and connected MCP servers."""
    return {"servers": [s.model_dump() for s in mcp_mgr.list_servers()]}


@app.get("/api/mcp/presets")
def get_mcp_presets():
    """List available ready-to-connect app presets."""
    return {"presets": [p.model_dump() for p in get_default_mcp_presets()]}


@app.post("/api/mcp/servers")
def register_mcp_server(config: MCPServerConfig):
    """Add a new custom or preset MCP server."""
    saved = mcp_mgr.register_server(config)
    return {"success": True, "server": saved.model_dump()}


@app.put("/api/mcp/servers/{server_id}/toggle")
def toggle_mcp_server(server_id: str, req: MCPToggleRequest):
    """Toggle connection status of an MCP server."""
    try:
        updated = mcp_mgr.toggle_server(server_id, enabled=req.enabled)
        return {"success": True, "server": updated.model_dump()}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")


@app.delete("/api/mcp/servers/{server_id}")
def remove_mcp_server(server_id: str):
    """Remove an MCP server configuration."""
    success = mcp_mgr.remove_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")
    return {"success": True, "removed_id": server_id}


@app.get("/api/mcp/servers/{server_id}/tools")
def list_mcp_server_tools(server_id: str):
    """List all tools exposed by an MCP server."""
    tools = mcp_mgr.list_tools_for_server(server_id)
    return {"server_id": server_id, "tools": [t.model_dump() for t in tools]}


@app.post("/api/mcp/servers/{server_id}/call-tool")
def call_mcp_tool(server_id: str, req: MCPToolCallRequest):
    """Execute a tool call on a connected MCP server."""
    try:
        res = mcp_mgr.call_tool(
            server_id=server_id,
            tool_name=req.tool_name,
            arguments=req.arguments,
        )
        return res
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/pipelines")
def get_mcp_pipelines():
    """List pre-built cross-app interoperability workflows."""
    return {"pipelines": [p.model_dump() for p in mcp_mgr.list_pipelines()]}


@app.post("/api/mcp/pipelines/execute")
def execute_mcp_pipeline(req: MCPPipelineExecuteRequest):
    """Execute a collaborative cross-app workflow where apps work together."""
    if req.custom_pipeline:
        pipeline = req.custom_pipeline
    elif req.pipeline_id:
        pipeline = mcp_mgr.get_pipeline(req.pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail=f"Pipeline '{req.pipeline_id}' not found")
    else:
        # Default to first available pipeline
        pipelines = mcp_mgr.list_pipelines()
        if not pipelines:
            raise HTTPException(status_code=400, detail="No pipelines available")
        pipeline = pipelines[0]

    result = mcp_mgr.execute_cross_app_pipeline(pipeline)
    return result.model_dump()


# ======================================================================
# USER ACCOUNT LOGIN & APP ACTIVITY LOG ENDPOINTS (Gemini, Canva, etc.)
# ======================================================================

@app.get("/api/accounts")
def get_user_accounts():
    """List external apps available for user account login and active session states."""
    accounts = account_mgr.list_accounts()
    return {"accounts": [a.model_dump() for a in accounts]}


@app.post("/api/accounts/login")
def login_user_account(req: AccountLoginRequest):
    """Log in to an external app as a user account, encrypting secrets in UserVault."""
    try:
        acct = account_mgr.login_account(req)
        return {"success": True, "account": acct.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/{app_id}/logout")
def logout_user_account(app_id: str):
    """Log out / disconnect user account from an external app."""
    try:
        acct = account_mgr.logout_account(app_id)
        return {"success": True, "account": acct.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/accounts/add-local")
def add_local_device_app(req: AddLocalAppRequest):
    """Register a custom local desktop app from user's device without requiring an API key."""
    try:
        acct = account_mgr.add_local_device_app(req)
        return {"success": True, "account": acct.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/add-custom")
def add_custom_app(req: AddCustomAppRequest):
    """Register a custom application with URL, API key, and user details (or local device app)."""
    try:
        acct = account_mgr.add_custom_app(req)
        return {"success": True, "account": acct.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts/logs")
def get_app_activity_logs(app_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 50):
    """Retrieve live activity and audit logs for app actions taken under user accounts."""
    etype = None
    if event_type:
        try:
            etype = AppEventType(event_type)
        except ValueError:
            pass
    logs = account_mgr.get_logs(app_id=app_id, event_type=etype, limit=limit)
    return {"logs": [l.model_dump() for l in logs]}


@app.delete("/api/accounts/logs")
def clear_app_activity_logs():
    """Clear app activity log history."""
    account_mgr.clear_logs()
    return {"success": True, "message": "App activity logs cleared."}


# ======================================================================
# System Version Handshake & MongoDB Connection Verification
# ======================================================================

class MongoVerifyRequest(BaseModel):
    uri: Optional[str] = None
    db_name: Optional[str] = None


@app.get("/api/system/version")
def get_system_version():
    """Version handshake between frontend and backend workstations."""
    db_status = mongo_manager.get_status()
    return {
        "backend_version": "1.2.0",
        "frontend_version_required": "1.2.x",
        "protocol_version": "v2.strawberry",
        "status": "operational",
        "database": db_status,
        "active_user": auth_manager.get_current_user().handle,
    }


@app.get("/api/db/status")
def get_database_status():
    """Retrieve MongoDB connection health, latency, and collection metrics."""
    return mongo_manager.get_status()


@app.post("/api/db/verify")
def verify_database_connection(req: MongoVerifyRequest):
    """Test and verify an arbitrary or configured MongoDB connection string (Atlas or Local)."""
    res = mongo_manager.verify_connection(uri=req.uri, db_name=req.db_name)
    return res


# ======================================================================
# Multi-Method Authentication & User Profile Endpoints
# ======================================================================

@app.get("/api/auth/me")
def get_my_profile():
    """Retrieve current authenticated user profile and connected methods."""
    user = auth_manager.get_current_user()
    return {"user": user.model_dump()}


@app.post("/api/auth/social")
def authenticate_social_account(req: SocialAuthRequest):
    """Authenticate or link account via Google, GitHub, or Facebook."""
    try:
        user = auth_manager.authenticate_social(req)
        return {"success": True, "user": user.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/passkey/register")
def register_passkey_credential(req: PasskeyRegisterRequest):
    """Register a new Passkey / WebAuthn / FIDO2 security key."""
    try:
        user = auth_manager.register_passkey(req)
        return {"success": True, "user": user.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/passkey/verify")
def verify_passkey_credential(req: PasskeyAuthRequest):
    """Authenticate and unlock session via Passkey biometric/security key."""
    try:
        user = auth_manager.verify_passkey(req)
        return {"success": True, "user": user.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/otp/send")
def send_verification_otp(req: OTPRequest):
    """Dispatch a 6-digit OTP code to email or phone number."""
    try:
        res = auth_manager.send_otp(req)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/otp/verify")
def verify_otp_code(req: OTPVerifyRequest):
    """Verify 6-digit OTP code and sign in / sign up user."""
    try:
        res = auth_manager.verify_otp(req)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/auth/profile")
def update_profile(req: ProfileUpdateRequest):
    """Update active user display name, handle, phone number, or avatar."""
    try:
        user = auth_manager.update_profile(req)
        return {"success": True, "user": user.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auth/users/search")
def search_users(q: str = ""):
    """Search registered Xeren users by handle, name, or email."""
    users = auth_manager.search_users(q)
    return {"users": [u.model_dump() for u in users]}


# ======================================================================
# Dual-Mode Projects (Solo & Group) and Member Collaboration
# ======================================================================

@app.get("/api/projects")
def list_projects():
    """List all Solo and Group projects."""
    projects = project_manager.list_projects()
    return {"projects": [p.model_dump() for p in projects]}


@app.post("/api/projects/create")
def create_project(req: ProjectCreateRequest):
    """Create a new Solo or Group project workspace."""
    try:
        proj = project_manager.create_project(req)
        return {"success": True, "project": proj.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    """Retrieve details for a specific project."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": proj.model_dump()}


@app.post("/api/projects/invite")
def invite_project_member(req: ProjectInviteRequest):
    """Invite a member via Xeren handle (in-app notification) or Email (verification link)."""
    try:
        invite = project_manager.invite_member(req)
        return {"success": True, "invite": invite.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/invites/{invite_id}/accept")
def accept_project_invite(invite_id: str):
    """Accept an in-app project invitation, immediately joining the collaborative workspace."""
    try:
        proj = project_manager.accept_invite(invite_id)
        return {"success": True, "project": proj.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/invites/{invite_id}/decline")
def decline_project_invite(invite_id: str):
    """Decline a project invitation."""
    try:
        invite = project_manager.decline_invite(invite_id)
        return {"success": True, "invite": invite.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/projects/join-code")
def join_project_by_code(req: ProjectJoinCodeRequest):
    """Join a project by entering a 6-digit email code or verification token."""
    try:
        proj = project_manager.join_by_code(req.code_or_token)
        return {"success": True, "project": proj.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/invites/pending")
def get_pending_user_invites(target: Optional[str] = None):
    """Retrieve pending invites matching user handle or email."""
    tgt = target or auth_manager.get_current_user().handle
    invites = project_manager.get_pending_invites_for_user(tgt)
    return {"invites": [i.model_dump() for i in invites]}


# ======================================================================
# Dedicated Project Coach Agent & Non-Interruptible Workstations
# ======================================================================

@app.get("/api/projects/{project_id}/coach/messages")
def get_coach_messages(project_id: str, member_id: Optional[str] = None):
    """Fetch isolated, non-polluting coaching conversation history for a specific member workstation."""
    user_id = member_id or auth_manager.get_current_user().user_id
    messages = project_manager.get_coach_history(project_id, user_id)
    return {"messages": [m.model_dump() for m in messages]}


@app.post("/api/projects/{project_id}/coach/chat")
def chat_with_project_coach(project_id: str, req: CoachChatRequest):
    """Ask doubt or seek technical guidance from Project Coach Agent with zero-interruption isolation."""
    try:
        req.project_id = project_id
        reply = project_manager.send_coach_message(req)
        return {"success": True, "message": reply.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/projects/{project_id}/specifications")
def update_project_specifications(project_id: str, req: ProjectSpecUpdateRequest):
    """Update technical specifications, architecture patterns, and constraints for the project."""
    try:
        proj = project_manager.update_specifications(project_id, req.specifications)
        return {"success": True, "project": proj.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/projects/{project_id}/members/{user_id}/role")
def update_project_member_role(project_id: str, user_id: str, req: MemberRoleUpdateRequest):
    """Assign or update member role and active sprint responsibilities."""
    try:
        proj = project_manager.update_member_role(
            project_id=project_id,
            user_id=user_id,
            new_role=req.role,
            active_task=req.active_task,
        )
        return {"success": True, "project": proj.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/workstations/heartbeat")
def heartbeat_workstation(project_id: str, req: WorkstationHeartbeatRequest):
    """Send heartbeat to maintain active workstation session without interrupting peer teammates."""
    try:
        ws = project_manager.heartbeat_workstation(
            project_id=project_id,
            user_id=req.member_user_id,
            active_task=req.active_task,
            status=req.status,
        )
        return {"success": True, "workstation": ws.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================================
# LLM Self-Improvement, Pattern Learning & Web/Bot Synthesis Endpoints
# ======================================================================

@app.get("/api/llm/improvements/status")
def get_llm_improvement_status():
    """Retrieve live self-improvement telemetry, adaptive score, and statistics."""
    report = llm_improvement_engine.get_status()
    return {"status": "ok", "report": report.model_dump()}


@app.get("/api/llm/improvements/patterns")
def get_user_query_patterns():
    """List patterns identified from repeated user queries, tasks, and preferred workflows."""
    patterns = llm_improvement_engine.list_patterns()
    return {"patterns": [p.model_dump() for p in patterns]}


@app.get("/api/llm/improvements/insights")
def get_search_and_model_insights():
    """List consensus knowledge and failure traps distilled from web searches and bot models."""
    insights = llm_improvement_engine.list_insights()
    return {"insights": [i.model_dump() for i in insights]}


@app.get("/api/llm/improvements/directives")
def get_adaptive_directives():
    """List active learned system directives that steer and optimize the LLM's prompts."""
    directives = llm_improvement_engine.list_directives()
    return {"directives": [d.model_dump() for d in directives]}


@app.post("/api/llm/improvements/analyze")
def trigger_self_improvement_analysis(req: Optional[AnalyzeImprovementsRequest] = None):
    """Trigger an on-demand self-improvement evolution cycle across all observations."""
    report = llm_improvement_engine.run_self_improvement_cycle(force=req.force_directive_synthesis if req else False)
    return {"success": True, "report": report.model_dump()}


@app.post("/api/llm/improvements/observe")
def record_learning_observation(req: RecordObservationRequest):
    """Ingest an interaction observation to continuously evolve patterns."""
    obs = llm_improvement_engine.record_observation(
        source=req.source,
        content=req.content,
        context=req.context,
        outcome_success=req.outcome_success,
    )
    return {"success": True, "observation": obs}


@app.put("/api/llm/improvements/directives/{directive_id}/toggle")
def toggle_adaptive_directive(directive_id: str, req: ToggleDirectiveRequest):
    """Enable or disable an active learned directive."""
    try:
        directive = llm_improvement_engine.toggle_directive(directive_id, req.is_active)
        return {"success": True, "directive": directive.model_dump()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))





