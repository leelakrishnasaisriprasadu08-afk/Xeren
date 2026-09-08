"""Pydantic schemas for Dual-Mode Projects, AI Coach Agent, and Non-Interruptible Workstations."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    SOLO = "solo"
    GROUP = "group"


class ProjectRole(str, Enum):
    OWNER = "owner"
    TECH_LEAD = "tech_lead"
    ARCHITECT = "architect"
    AI_SPECIALIST = "ai_specialist"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    ADMIN = "admin"
    EDITOR = "editor"


class InviteType(str, Enum):
    XEREN_ACCOUNT = "xeren_account"
    EMAIL = "email"


class InviteStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class ProjectMember(BaseModel):
    user_id: str
    handle: str
    display_name: str
    email: str
    role: str = "editor"
    joined_at: str
    avatar_url: Optional[str] = None
    is_owner: bool = False
    active_task: Optional[str] = "Collaborative session"


class ProjectMilestone(BaseModel):
    milestone_id: str
    title: str
    description: str
    assigned_role: str = "engineer"
    assigned_member_handle: Optional[str] = None
    status: str = "in_progress"  # "pending" | "in_progress" | "completed"
    due_date: Optional[str] = None


class ProjectSpecification(BaseModel):
    tech_stack: List[str] = Field(default_factory=list)
    architecture_pattern: str = "Event-driven Modular Architecture"
    constraints: List[str] = Field(default_factory=list)
    target_apis: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    repository_url: Optional[str] = None


class ProjectCoachMessage(BaseModel):
    message_id: str
    project_id: str
    member_user_id: str
    member_handle: str
    sender: str  # "user" | "coach_agent"
    content: str
    timestamp: str
    role_context: Optional[str] = None
    session_id: Optional[str] = None


class ProjectWorkstationSession(BaseModel):
    workstation_id: str
    project_id: str
    member_user_id: str
    member_handle: str
    member_role: str
    active_task: str
    status: str = "active"  # "active" | "idle" | "coding" | "debugging"
    last_heartbeat: str


class ProjectInvite(BaseModel):
    invite_id: str
    project_id: str
    project_name: str
    invite_type: InviteType
    recipient: str = Field(description="Xeren handle (@handle) or email address")
    role: str = "editor"
    token: str
    verification_code: str
    status: InviteStatus = InviteStatus.PENDING
    created_at: str
    expires_at: str
    sender_id: str
    sender_name: str
    sender_handle: str
    mail_dispatch_status: Optional[str] = None


class Project(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    project_type: ProjectType = ProjectType.SOLO
    owner_id: str
    owner_name: str
    owner_handle: str
    created_at: str
    updated_at: str
    members: List[ProjectMember] = Field(default_factory=list)
    invites: List[ProjectInvite] = Field(default_factory=list)
    specifications: ProjectSpecification = Field(default_factory=ProjectSpecification)
    milestones: List[ProjectMilestone] = Field(default_factory=list)
    active_workstations: List[ProjectWorkstationSession] = Field(default_factory=list)
    workspace_path: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    synced_with_mongo: bool = False


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: ProjectType = ProjectType.SOLO
    tags: List[str] = Field(default_factory=list)
    workspace_path: Optional[str] = None
    initial_invites: List[ProjectInviteRequest] = Field(default_factory=list)
    specifications: Optional[ProjectSpecification] = None


class ProjectInviteRequest(BaseModel):
    project_id: str
    invite_type: InviteType = InviteType.XEREN_ACCOUNT
    target: str = Field(description="Xeren username/handle (@sarah_ai) or email address")
    role: str = "editor"


class ProjectJoinCodeRequest(BaseModel):
    code_or_token: str


class CoachChatRequest(BaseModel):
    project_id: str
    member_user_id: str
    message: str
    role_context: Optional[str] = None


class ProjectSpecUpdateRequest(BaseModel):
    specifications: ProjectSpecification


class MemberRoleUpdateRequest(BaseModel):
    role: str
    active_task: Optional[str] = None


class WorkstationHeartbeatRequest(BaseModel):
    member_user_id: str
    active_task: str
    status: str = "active"
