"""Project Coach Agent: Isolated, Role-Contextualized AI Mentorship for Project Workstations."""

from __future__ import annotations

import logging
import secrets
import time
from typing import Dict, List, Optional

from xeren.models.improvement.engine import llm_improvement_engine
from xeren.models.improvement.schemas import ObservationSource
from xeren.projects.schemas import (
    CoachChatRequest,
    Project,
    ProjectCoachMessage,
    ProjectRole,
    ProjectSpecification,
)

logger = logging.getLogger("xeren.projects.coach")


class ProjectCoachAgent:
    """Intelligent coaching agent that mentors project members in isolated workstation streams.
    
    Guarantees:
    1. Zero-interruption / Zero-bleeding: Message histories are segregated by (project_id, member_user_id).
    2. Deep Contextualization: Answers are framed using project technical specs, architecture patterns,
       member's assigned role, and current milestone tasks.
    3. Isolated History: Never pollutes or overlaps with main Xeren chat history.
    """

    def __init__(self) -> None:
        # Key: f"{project_id}_{member_user_id}" -> List of ProjectCoachMessage
        self._history_stores: Dict[str, List[ProjectCoachMessage]] = {}
        self._seed_default_conversations()

    def _get_key(self, project_id: str, member_user_id: str) -> str:
        return f"{project_id}_{member_user_id}"

    def _seed_default_conversations(self) -> None:
        """Seed initial contextual messages for default demo projects."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Seed welcome message for dev user in cyberforge
        dev_key = self._get_key("proj_cyberforge_group", "usr_dev_01")
        self._history_stores[dev_key] = [
            ProjectCoachMessage(
                message_id="pcm_seed_01",
                project_id="proj_cyberforge_group",
                member_user_id="usr_dev_01",
                member_handle="@xeren_dev",
                sender="coach_agent",
                content=(
                    "Welcome to CyberForge AI Engine workstation, Lead Architect! I am your dedicated "
                    "Project Coach Agent. I have loaded the project specifications: Event-driven Modular Architecture, "
                    "FastAPI backend, React 19 frontend, and MongoDB sync. How can I assist you with your current sprint tasks?"
                ),
                timestamp=now,
                role_context="Tech Lead / Architect",
                session_id="session_dev_01",
            )
        ]

        # Seed separate message for Sarah in her isolated workstation
        sarah_key = self._get_key("proj_cyberforge_group", "usr_peer_02")
        self._history_stores[sarah_key] = [
            ProjectCoachMessage(
                message_id="pcm_seed_02",
                project_id="proj_cyberforge_group",
                member_user_id="usr_peer_02",
                member_handle="@sarah_ai",
                sender="coach_agent",
                content=(
                    "Hello Dr. Chen! As the project AI Specialist, I am ready to guide you on model fine-tuning "
                    "benchmarks and multi-agent reasoning orchestration within CyberForge."
                ),
                timestamp=now,
                role_context="AI Specialist",
                session_id="session_sarah_02",
            )
        ]

    def get_messages(self, project_id: str, member_user_id: str) -> List[ProjectCoachMessage]:
        """Fetch isolated conversation history for a specific member in a project."""
        key = self._get_key(project_id, member_user_id)
        if key not in self._history_stores:
            self._history_stores[key] = []
        return list(self._history_stores[key])

    def post_user_message(
        self,
        project_id: str,
        member_user_id: str,
        member_handle: str,
        content: str,
        role_context: Optional[str] = None,
    ) -> ProjectCoachMessage:
        """Store user message into their isolated workstation stream."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        msg = ProjectCoachMessage(
            message_id=f"pcm_{secrets.token_hex(6)}",
            project_id=project_id,
            member_user_id=member_user_id,
            member_handle=member_handle,
            sender="user",
            content=content,
            timestamp=now,
            role_context=role_context,
            session_id=f"sess_{member_user_id}",
        )
        key = self._get_key(project_id, member_user_id)
        if key not in self._history_stores:
            self._history_stores[key] = []
        self._history_stores[key].append(msg)
        return msg

    def post_coach_reply(
        self,
        project_id: str,
        member_user_id: str,
        member_handle: str,
        content: str,
        role_context: Optional[str] = None,
    ) -> ProjectCoachMessage:
        """Store coach agent reply into member's isolated workstation stream."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        msg = ProjectCoachMessage(
            message_id=f"pcm_{secrets.token_hex(6)}",
            project_id=project_id,
            member_user_id=member_user_id,
            member_handle=member_handle,
            sender="coach_agent",
            content=content,
            timestamp=now,
            role_context=role_context,
            session_id=f"sess_{member_user_id}",
        )
        key = self._get_key(project_id, member_user_id)
        if key not in self._history_stores:
            self._history_stores[key] = []
        self._history_stores[key].append(msg)
        return msg

    def answer_query(
        self,
        req: CoachChatRequest,
        project: Project,
        member_handle: str,
        member_role: str,
    ) -> ProjectCoachMessage:
        """Generate a role-tailored, specification-grounded coaching reply without interrupting others."""
        # 1. Record member's question in local stream and self-improvement engine
        self.post_user_message(
            project_id=project.project_id,
            member_user_id=req.member_user_id,
            member_handle=member_handle,
            content=req.message,
            role_context=member_role,
        )
        llm_improvement_engine.record_observation(
            source=ObservationSource.USER_QUERY,
            content=req.message,
            context={"role": member_role, "project_id": project.project_id},
        )

        # 2. Synthesize guidance based on project specifications and member role
        coach_response_text = self._synthesize_guidance(
            query=req.message,
            project=project,
            role=member_role,
            handle=member_handle,
        )

        # 3. Post reply to isolated stream
        reply = self.post_coach_reply(
            project_id=project.project_id,
            member_user_id=req.member_user_id,
            member_handle=member_handle,
            content=coach_response_text,
            role_context=f"Coach Guidance for {member_role.replace('_', ' ').title()}",
        )
        return reply

    def _synthesize_guidance(
        self,
        query: str,
        project: Project,
        role: str,
        handle: str,
    ) -> str:
        """Formulate rich, context-aware coaching response tailored to member's role and project specs."""
        q = query.lower().strip()
        specs = project.specifications or ProjectSpecification()
        tech_stack_str = ", ".join(specs.tech_stack) if specs.tech_stack else "Standard Python/TypeScript stack"
        arch = specs.architecture_pattern or "Modular Micro-services Architecture"
        constraints = specs.constraints or ["Zero latency leakage", "Strict type-safety"]

        role_clean = role.lower().replace(" ", "_")

        # Specific domain answering:
        if "architecture" in q or "structure" in q or "pattern" in q:
            return (
                f"### [Architecture Guidance for {role.replace('_', ' ').title()}]\n\n"
                f"For **{project.name}**, we adhere strictly to **{arch}**.\n\n"
                f"**Key Guidelines**:\n"
                f"- **Decoupled Components**: Ensure all service boundaries communicate via typed schemas.\n"
                f"- **Tech Stack Alignment**: Use `{tech_stack_str}` across modules.\n"
                f"- **Active Constraints**: {', '.join(constraints)}.\n\n"
                f"Next action: Align your module interfaces with the existing project milestones."
            )

        if "role" in q or "responsibility" in q or "what should i do" in q:
            role_duties = {
                "owner": "Oversee overall project trajectory, approve milestone releases, and manage member invitations.",
                "tech_lead": "Direct technical architecture, enforce engineering constraints, and ensure zero-interruption workstation throughput.",
                "architect": "Design modular component boundaries, define data schemas, and validate high-level API contracts.",
                "ai_specialist": "Optimize model inference pipelines, prompt engineering benchmarks, and tool-agent orchestration.",
                "engineer": "Implement core business logic, write rigorous automated tests, and submit PRs matching specs.",
                "reviewer": "Audit code quality, verify security constraints, and review architectural compliance.",
                "viewer": "Inspect real-time project progress, review specifications, and monitor milestone completion.",
                "editor": "Collaborate on features, update specs, and maintain code modules.",
            }
            duty = role_duties.get(role_clean, "Collaborate on project milestones according to assigned tasks.")
            return (
                f"### [Role Focus: {role.replace('_', ' ').title()}]\n\n"
                f"Hi {handle}! Your primary objective in **{project.name}** is:\n"
                f"> *{duty}*\n\n"
                f"Current project architecture: **{arch}**.\n"
                f"You have active access to your independent workstation with zero interruption from teammates."
            )

        if "milestone" in q or "deliverable" in q or "progress" in q:
            milestones = project.milestones
            if milestones:
                items = [f"- **{m.title}** (`{m.status}`): {m.description}" for m in milestones[:4]]
                return (
                    f"### [Sprint Milestones for {project.name}]\n\n"
                    f"Here are the active deliverables:\n" + "\n".join(items) + "\n\n"
                    f"Focus on your assigned role deliverables to keep the sprint green!"
                )
            return f"No pending milestones recorded for **{project.name}**. You can register new milestones in the Specifications tab."

        if "doubt" in q or "help" in q or "error" in q or "bug" in q:
            return (
                f"### [Workstation Troubleshooting Support]\n\n"
                f"I'm analyzing your doubt for **{project.name}**:\n"
                f"- **Your Session**: Workstation is completely isolated from other teammates so you can experiment freely.\n"
                f"- **Constraints to check**: {', '.join(constraints[:3])}.\n"
                f"- **Recommended step**: Inspect your local test runner or module logs. If you share the exact snippet or error message, I will pinpoint the exact fix for `{tech_stack_str}`."
            )

        # General contextual mentorship
        return (
            f"### [Project Coach Advisory]\n\n"
            f"Understood, {handle}. For **{project.name}** (pattern: *{arch}*), "
            f"I recommend approaching this from your **{role.replace('_', ' ').title()}** perspective:\n\n"
            f"1. Check the target specifications ({tech_stack_str}).\n"
            f"2. Ensure any schema additions respect project constraints: {constraints[0] if constraints else 'Type safety'}.\n"
            f"3. Your workstation session is running in parallel without any interference from other members.\n\n"
            f"Feel free to ask for architectural diagrams, code templates, or verification checklists!"
        )


# Global singleton coach agent
project_coach_agent = ProjectCoachAgent()
