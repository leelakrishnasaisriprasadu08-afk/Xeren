export type ProjectType = 'solo' | 'group'

export type ProjectRole =
  | 'owner'
  | 'tech_lead'
  | 'architect'
  | 'ai_specialist'
  | 'engineer'
  | 'reviewer'
  | 'viewer'
  | 'admin'
  | 'editor'

export type InviteType = 'xeren_account' | 'email'

export type InviteStatus = 'pending' | 'accepted' | 'declined' | 'expired'

export interface ProjectMember {
  user_id: string
  handle: string
  display_name: string
  email: string
  role: ProjectRole
  joined_at: string
  avatar_url?: string
  is_owner?: boolean
  active_task?: string
}

export interface ProjectMilestone {
  milestone_id: string
  title: string
  description: string
  assigned_role: ProjectRole
  assigned_member_handle?: string
  status: 'pending' | 'in_progress' | 'completed'
  due_date?: string
}

export interface ProjectSpecification {
  tech_stack: string[]
  architecture_pattern: string
  constraints: string[]
  target_apis: string[]
  deliverables: string[]
  repository_url?: string
}

export interface ProjectCoachMessage {
  message_id: string
  project_id: string
  member_user_id: string
  member_handle: string
  sender: 'user' | 'coach_agent'
  content: string
  timestamp: string
  role_context?: string
  session_id?: string
}

export interface ProjectWorkstationSession {
  workstation_id: string
  project_id: string
  member_user_id: string
  member_handle: string
  member_role: ProjectRole
  active_task: string
  status: 'active' | 'idle' | 'coding' | 'debugging'
  last_heartbeat: string
}

export interface ProjectInvite {
  invite_id: string
  project_id: string
  project_name: string
  invite_type: InviteType
  recipient: string
  role: ProjectRole
  token: string
  verification_code: string
  status: InviteStatus
  created_at: string
  expires_at: string
  sender_id: string
  sender_name: string
  sender_handle: string
  mail_dispatch_status?: string
}

export interface Project {
  project_id: string
  name: string
  description?: string
  project_type: ProjectType
  owner_id: string
  owner_name: string
  owner_handle: string
  created_at: string
  updated_at: string
  members: ProjectMember[]
  invites: ProjectInvite[]
  specifications?: ProjectSpecification
  milestones?: ProjectMilestone[]
  active_workstations?: ProjectWorkstationSession[]
  workspace_path?: string
  tags: string[]
  synced_with_mongo?: boolean
}

export interface ProjectCreatePayload {
  name: string
  description?: string
  project_type: ProjectType
  tags?: string[]
  workspace_path?: string
  initial_invites?: Array<{
    project_id: string
    invite_type: InviteType
    target: string
    role: ProjectRole
  }>
  specifications?: ProjectSpecification
}

export interface CoachChatPayload {
  project_id: string
  member_user_id: string
  message: string
  role_context?: string
}

export interface ProjectSpecUpdatePayload {
  specifications: ProjectSpecification
}

export interface MemberRoleUpdatePayload {
  role: ProjectRole
  active_task?: string
}

export interface WorkstationHeartbeatPayload {
  member_user_id: string
  active_task: string
  status?: string
}

