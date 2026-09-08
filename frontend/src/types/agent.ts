/**
 * Agent phase and activity progress schemas for frontend visualization.
 */

export type AgentPhase =
  | 'understanding'
  | 'planning'
  | 'researching'
  | 'creating'
  | 'verifying'
  | 'completed'

export type AgentMilestone = AgentPhase

export interface ActivityItem {
  id: string
  phase: AgentPhase
  title: string
  description?: string
  timestamp: number
  completed: boolean
}

export interface TaskProgress {
  taskId: string
  goal: string
  currentPhase: AgentPhase
  active: boolean
  progressPercent: number
  activities: ActivityItem[]
}

export interface AgentProgressDetails {
  phase?: AgentPhase
  goal?: string
  milestone?: AgentMilestone
  progress_percent?: number
  action_type?: string
  active_tool?: string
}
