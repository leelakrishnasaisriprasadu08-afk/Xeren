"""ProjectManager for Solo & Group Workspaces, Member Invites, and Real-time Sync."""

from __future__ import annotations

import logging
import random
import secrets
import time
from typing import Any, Dict, List, Optional

from xeren.auth.manager import AuthManager, auth_manager
from xeren.auth.schemas import UserProfile
from xeren.db.mongo import MongoConnectionManager, mongo_manager
from xeren.projects.coach import ProjectCoachAgent, project_coach_agent
from xeren.projects.schemas import (
    CoachChatRequest,
    InviteStatus,
    InviteType,
    Project,
    ProjectCoachMessage,
    ProjectCreateRequest,
    ProjectInvite,
    ProjectInviteRequest,
    ProjectMember,
    ProjectMilestone,
    ProjectRole,
    ProjectSpecification,
    ProjectType,
    ProjectWorkstationSession,
)

logger = logging.getLogger("xeren.projects.manager")


class ProjectManager:
    """Manages Solo and Collaborative Group Workspaces and Member Onboarding."""

    def __init__(
        self,
        auth_mgr: Optional[AuthManager] = None,
        db: Optional[MongoConnectionManager] = None,
        coach: Optional[ProjectCoachAgent] = None,
    ) -> None:
        self.auth_mgr = auth_mgr or auth_manager
        self.db = db or mongo_manager
        self.coach_agent = coach or project_coach_agent
        self._projects: Dict[str, Project] = {}
        self._invites: Dict[str, ProjectInvite] = {}

        self._seed_default_projects()

    def _seed_default_projects(self) -> None:
        """Seed initial solo and collaborative projects with rich specifications, roles, and milestones."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        dev_user = self.auth_mgr.get_current_user()

        # 1. Default Solo Project
        solo_project = Project(
            project_id="proj_xeren_core",
            name="Xeren Autonomous Core",
            description="Private autonomous workstation for deep chain-of-thought Strawberry reasoning and local tool execution.",
            project_type=ProjectType.SOLO,
            owner_id=dev_user.user_id,
            owner_name=dev_user.display_name,
            owner_handle=dev_user.handle,
            created_at=now,
            updated_at=now,
            members=[
                ProjectMember(
                    user_id=dev_user.user_id,
                    handle=dev_user.handle,
                    display_name=dev_user.display_name,
                    email=dev_user.email,
                    role=ProjectRole.OWNER.value,
                    joined_at=now,
                    avatar_url=dev_user.avatar_url,
                    is_owner=True,
                    active_task="Refining Strawberry reasoning planner loops",
                )
            ],
            invites=[],
            specifications=ProjectSpecification(
                tech_stack=["Python 3.12", "FastAPI", "React 19", "Strawberry CoT", "SQLite-vec"],
                architecture_pattern="Autonomous Local-First Agent Framework",
                constraints=["Zero telemetry leakage", "Sandboxed execution", "100% test coverage"],
                target_apis=["Local LLM inference", "MCP protocol", "File system watcher"],
                deliverables=["Single-binary packaging", "Autonomous self-healing engine"],
            ),
            milestones=[
                ProjectMilestone(
                    milestone_id="ms_solo_01",
                    title="Strawberry CoT Reasoning Engine",
                    description="Finalize deep chain-of-thought planner and reflection loops",
                    assigned_role=ProjectRole.OWNER.value,
                    assigned_member_handle=dev_user.handle,
                    status="completed",
                ),
                ProjectMilestone(
                    milestone_id="ms_solo_02",
                    title="Autonomous Execution Sandbox",
                    description="Enforce isolated process sandboxing for command execution",
                    assigned_role=ProjectRole.OWNER.value,
                    assigned_member_handle=dev_user.handle,
                    status="in_progress",
                ),
            ],
            active_workstations=[
                ProjectWorkstationSession(
                    workstation_id="ws_dev_solo",
                    project_id="proj_xeren_core",
                    member_user_id=dev_user.user_id,
                    member_handle=dev_user.handle,
                    member_role=ProjectRole.OWNER.value,
                    active_task="Refining Strawberry reflection tree",
                    status="active",
                    last_heartbeat=now,
                )
            ],
            workspace_path="C:/Users/leela/OneDrive/Desktop/Xeren/Xeren",
            tags=["autonomous", "strawberry", "vault", "local-first"],
            synced_with_mongo=True,
        )
        self.save_project(solo_project)

        # 2. Collaborative Group Project
        group_project = Project(
            project_id="proj_cyberforge_group",
            name="CyberForge AI Engine",
            description="Collaborative team project for multi-model autonomous agent development and distributed deployment.",
            project_type=ProjectType.GROUP,
            owner_id=dev_user.user_id,
            owner_name=dev_user.display_name,
            owner_handle=dev_user.handle,
            created_at=now,
            updated_at=now,
            members=[
                ProjectMember(
                    user_id=dev_user.user_id,
                    handle=dev_user.handle,
                    display_name=dev_user.display_name,
                    email=dev_user.email,
                    role=ProjectRole.ARCHITECT.value,
                    joined_at=now,
                    avatar_url=dev_user.avatar_url,
                    is_owner=True,
                    active_task="Designing zero-interruption workstation pipelines",
                ),
                ProjectMember(
                    user_id="usr_peer_02",
                    handle="@sarah_ai",
                    display_name="Dr. Sarah Chen",
                    email="sarah.chen@deepmind-labs.org",
                    role=ProjectRole.AI_SPECIALIST.value,
                    joined_at=now,
                    avatar_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&q=80",
                    is_owner=False,
                    active_task="Fine-tuning prompt reasoning templates",
                ),
            ],
            invites=[],
            specifications=ProjectSpecification(
                tech_stack=["TypeScript", "FastAPI", "MongoDB Atlas", "React 19", "WebSockets"],
                architecture_pattern="Distributed Multi-Agent Event Bus",
                constraints=[
                    "Zero-interruption workstation isolation",
                    "Strict role-based action gating",
                    "Real-time sync latency < 50ms",
                ],
                target_apis=["OpenAI API", "Anthropic Claude API", "Gemini Pro API", "MongoDB Atlas"],
                deliverables=[
                    "Parallel collaborative workstations",
                    "AI Coach integration",
                    "Role matrix management",
                ],
            ),
            milestones=[
                ProjectMilestone(
                    milestone_id="ms_grp_01",
                    title="Real-time Workstation Event Bus",
                    description="Deploy WebSocket multiplexer for zero-lag peer collaboration",
                    assigned_role=ProjectRole.ARCHITECT.value,
                    assigned_member_handle=dev_user.handle,
                    status="completed",
                ),
                ProjectMilestone(
                    milestone_id="ms_grp_02",
                    title="Multi-Model Reasoning Benchmarks",
                    description="Benchmark Claude 3.5 Sonnet vs Gemini 2.0 Flash for sub-agents",
                    assigned_role=ProjectRole.AI_SPECIALIST.value,
                    assigned_member_handle="@sarah_ai",
                    status="in_progress",
                ),
                ProjectMilestone(
                    milestone_id="ms_grp_03",
                    title="RBAC Security Gate Auditing",
                    description="Enforce role permissions between Architect, Engineer, and Reviewer",
                    assigned_role=ProjectRole.ENGINEER.value,
                    assigned_member_handle=dev_user.handle,
                    status="pending",
                ),
            ],
            active_workstations=[
                ProjectWorkstationSession(
                    workstation_id="ws_dev_grp",
                    project_id="proj_cyberforge_group",
                    member_user_id=dev_user.user_id,
                    member_handle=dev_user.handle,
                    member_role=ProjectRole.ARCHITECT.value,
                    active_task="Designing zero-interruption workstation pipelines",
                    status="active",
                    last_heartbeat=now,
                ),
                ProjectWorkstationSession(
                    workstation_id="ws_sarah_grp",
                    project_id="proj_cyberforge_group",
                    member_user_id="usr_peer_02",
                    member_handle="@sarah_ai",
                    member_role=ProjectRole.AI_SPECIALIST.value,
                    active_task="Fine-tuning prompt reasoning templates",
                    status="active",
                    last_heartbeat=now,
                ),
            ],
            workspace_path="C:/Users/leela/Projects/CyberForge",
            tags=["team", "collaboration", "neural", "sync"],
            synced_with_mongo=True,
        )
        self.save_project(group_project)

    def save_project(self, project: Project) -> None:
        """Persist project to memory and MongoDB."""
        self._projects[project.project_id] = project
        if self.db:
            self.db.insert_document("projects", project.project_id, project.model_dump())

    def list_projects(self) -> List[Project]:
        """List all projects available to workstation."""
        return list(self._projects.values())

    def get_project(self, project_id: str) -> Optional[Project]:
        """Fetch project by ID."""
        if project_id in self._projects:
            return self._projects[project_id]
        if self.db:
            data = self.db.find_document("projects", project_id)
            if data:
                p = Project(**data)
                self._projects[p.project_id] = p
                return p
        return None

    def create_project(
        self,
        req: ProjectCreateRequest,
        creator: Optional[UserProfile] = None,
    ) -> Project:
        """Create a new Solo or Group project."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        user = creator or self.auth_mgr.get_current_user()

        project_id = f"proj_{secrets.token_hex(6)}"
        owner_member = ProjectMember(
            user_id=user.user_id,
            handle=user.handle,
            display_name=user.display_name,
            email=user.email,
            role=ProjectRole.OWNER,
            joined_at=now,
            avatar_url=user.avatar_url,
            is_owner=True,
        )

        project = Project(
            project_id=project_id,
            name=req.name.strip(),
            description=req.description.strip() if req.description else "",
            project_type=req.project_type,
            owner_id=user.user_id,
            owner_name=user.display_name,
            owner_handle=user.handle,
            created_at=now,
            updated_at=now,
            members=[owner_member],
            invites=[],
            workspace_path=req.workspace_path or f"C:/Users/leela/Projects/{req.name.strip().replace(' ', '_')}",
            tags=req.tags,
            synced_with_mongo=self.db.is_connected,
        )

        # Dispatch initial invites if requested (for Group projects)
        for inv_req in req.initial_invites:
            inv_req.project_id = project_id
            self.invite_member(inv_req, sender=user, project=project)

        self.save_project(project)
        user.active_project_id = project.project_id
        self.auth_mgr.save_user(user)

        logger.info("Project created: '%s' (type=%s, id=%s)", project.name, project.project_type, project_id)
        return project

    def invite_member(
        self,
        req: ProjectInviteRequest,
        sender: Optional[UserProfile] = None,
        project: Optional[Project] = None,
    ) -> ProjectInvite:
        """Invite a member via Xeren handle or Email address."""
        proj = project or self.get_project(req.project_id)
        if not proj:
            raise KeyError(f"Project with ID '{req.project_id}' not found")

        user = sender or self.auth_mgr.get_current_user()
        target = req.target.strip()
        if not target:
            raise ValueError("Invitation target (handle or email) cannot be empty")

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        invite_id = f"inv_{secrets.token_hex(6)}"
        token = f"xrn_join_{secrets.token_urlsafe(16)}"
        verification_code = f"{random.randint(100000, 999999)}"
        expires_at = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 7 * 86400)
        )  # 7 days

        # Determine dispatch mode
        if req.invite_type == InviteType.XEREN_ACCOUNT:
            if not target.startswith("@"):
                target = f"@{target}"
            dispatch_status = "in_app_notification_delivered"
        else:
            dispatch_status = "verification_email_dispatched"

        invite = ProjectInvite(
            invite_id=invite_id,
            project_id=proj.project_id,
            project_name=proj.name,
            invite_type=req.invite_type,
            recipient=target,
            role=req.role,
            token=token,
            verification_code=verification_code,
            status=InviteStatus.PENDING,
            created_at=now,
            expires_at=expires_at,
            sender_id=user.user_id,
            sender_name=user.display_name,
            sender_handle=user.handle,
            mail_dispatch_status=dispatch_status,
        )

        proj.invites.append(invite)
        proj.updated_at = now
        self._invites[invite_id] = invite
        self.save_project(proj)

        if self.db:
            self.db.insert_document("invites", invite_id, invite.model_dump())

        logger.info(
            "Dispatched invite to %s (%s) for project '%s'",
            target,
            req.invite_type,
            proj.name,
        )
        return invite

    def accept_invite(
        self,
        invite_id: str,
        user: Optional[UserProfile] = None,
    ) -> Project:
        """Accept an in-app or email project invite, adding member to project."""
        invite = self._invites.get(invite_id)
        if not invite:
            # Check DB
            data = self.db.find_document("invites", invite_id) if self.db else None
            if data:
                invite = ProjectInvite(**data)
                self._invites[invite.invite_id] = invite
            else:
                raise KeyError(f"Invite with ID '{invite_id}' not found")

        if invite.status != InviteStatus.PENDING:
            raise ValueError(f"Invite is already in status '{invite.status}'")

        proj = self.get_project(invite.project_id)
        if not proj:
            raise KeyError(f"Project '{invite.project_id}' does not exist")

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        joining_user = user or self.auth_mgr.get_current_user()

        # Check if already a member
        existing = next((m for m in proj.members if m.user_id == joining_user.user_id), None)
        if not existing:
            new_member = ProjectMember(
                user_id=joining_user.user_id,
                handle=joining_user.handle,
                display_name=joining_user.display_name,
                email=joining_user.email,
                role=invite.role,
                joined_at=now,
                avatar_url=joining_user.avatar_url,
                is_owner=False,
            )
            proj.members.append(new_member)

        invite.status = InviteStatus.ACCEPTED
        proj.updated_at = now
        self.save_project(proj)

        if self.db:
            self.db.insert_document("invites", invite.invite_id, invite.model_dump())

        logger.info(
            "User %s accepted invite and joined project '%s'",
            joining_user.handle,
            proj.name,
        )
        return proj

    def decline_invite(self, invite_id: str) -> ProjectInvite:
        """Decline a project invitation."""
        invite = self._invites.get(invite_id)
        if not invite:
            raise KeyError(f"Invite '{invite_id}' not found")

        invite.status = InviteStatus.DECLINED
        proj = self.get_project(invite.project_id)
        if proj:
            proj.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.save_project(proj)

        if self.db:
            self.db.insert_document("invites", invite.invite_id, invite.model_dump())

        return invite

    def join_by_code(
        self,
        code_or_token: str,
        user: Optional[UserProfile] = None,
    ) -> Project:
        """Join a project by entering the 6-digit email code or join token."""
        query = code_or_token.strip()
        matched_invite = None

        for inv in self._invites.values():
            if inv.status == InviteStatus.PENDING and (
                inv.verification_code == query or inv.token == query
            ):
                matched_invite = inv
                break

        if not matched_invite:
            # Also search projects' embedded invites
            for p in self._projects.values():
                for inv in p.invites:
                    if inv.status == InviteStatus.PENDING and (
                        inv.verification_code == query or inv.token == query
                    ):
                        matched_invite = inv
                        break
                if matched_invite:
                    break

        if not matched_invite:
            raise ValueError("Invalid or expired verification code / invitation link")

        return self.accept_invite(matched_invite.invite_id, user=user)

    def get_pending_invites_for_user(self, handle_or_email: str) -> List[ProjectInvite]:
        """Fetch pending invites matching user handle or email."""
        h = handle_or_email.strip().lower()
        results = []
        for inv in self._invites.values():
            if inv.status == InviteStatus.PENDING and (
                inv.recipient.lower() == h or inv.recipient.lower() == f"@{h.lstrip('@')}"
            ):
                results.append(inv)
        return results

    def get_coach_history(self, project_id: str, member_user_id: str) -> List[ProjectCoachMessage]:
        """Fetch isolated conversation history between Project Coach and this specific member."""
        return self.coach_agent.get_messages(project_id, member_user_id)

    def send_coach_message(self, req: CoachChatRequest) -> ProjectCoachMessage:
        """Post a member doubt to the coach and receive non-interruptible, role-grounded guidance."""
        proj = self.get_project(req.project_id)
        if not proj:
            raise KeyError(f"Project '{req.project_id}' not found")

        member = next((m for m in proj.members if m.user_id == req.member_user_id), None)
        handle = member.handle if member else "@unknown_member"
        role = req.role_context or (member.role if member else "engineer")

        return self.coach_agent.answer_query(
            req=req,
            project=proj,
            member_handle=handle,
            member_role=role,
        )

    def update_specifications(self, project_id: str, specs: ProjectSpecification) -> Project:
        """Update technical specifications and architecture blueprint for the project."""
        proj = self.get_project(project_id)
        if not proj:
            raise KeyError(f"Project '{project_id}' not found")
        proj.specifications = specs
        proj.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save_project(proj)
        return proj

    def update_member_role(
        self,
        project_id: str,
        user_id: str,
        new_role: str,
        active_task: Optional[str] = None,
    ) -> Project:
        """Update role and responsibilities for a project member and sync workstation session."""
        proj = self.get_project(project_id)
        if not proj:
            raise KeyError(f"Project '{project_id}' not found")

        member = next((m for m in proj.members if m.user_id == user_id), None)
        if not member:
            raise KeyError(f"Member '{user_id}' not found in project '{project_id}'")

        member.role = new_role
        if active_task:
            member.active_task = active_task

        # Also update active workstation session if present
        ws = next((w for w in proj.active_workstations if w.member_user_id == user_id), None)
        if ws:
            ws.member_role = new_role
            if active_task:
                ws.active_task = active_task
            ws.last_heartbeat = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        proj.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save_project(proj)
        return proj

    def heartbeat_workstation(
        self,
        project_id: str,
        user_id: str,
        active_task: str,
        status: str = "active",
    ) -> ProjectWorkstationSession:
        """Register or update an active member workstation session to reflect live status."""
        proj = self.get_project(project_id)
        if not proj:
            raise KeyError(f"Project '{project_id}' not found")

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        member = next((m for m in proj.members if m.user_id == user_id), None)
        handle = member.handle if member else "@unknown"
        role = member.role if member else "engineer"

        ws = next((w for w in proj.active_workstations if w.member_user_id == user_id), None)
        if ws:
            ws.active_task = active_task
            ws.status = status
            ws.last_heartbeat = now
            ws.member_role = role
        else:
            ws = ProjectWorkstationSession(
                workstation_id=f"ws_{secrets.token_hex(4)}",
                project_id=project_id,
                member_user_id=user_id,
                member_handle=handle,
                member_role=role,
                active_task=active_task,
                status=status,
                last_heartbeat=now,
            )
            proj.active_workstations.append(ws)

        proj.updated_at = now
        self.save_project(proj)
        return ws


# Global singleton instance
project_manager = ProjectManager()

