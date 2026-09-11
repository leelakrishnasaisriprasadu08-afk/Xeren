/**
 * Message and transcript schema definitions.
 */

export type MessageRole = 'user' | 'xeren' | 'assistant' | 'system'

export type MessageStatus = 'streaming' | 'complete' | 'error' | 'interrupted'

export interface StagedPlanStep {
  id?: number | string
  description?: string
  status?: 'pending' | 'executing' | 'completed' | 'failed'
  action_type?: string
  tool?: string
}

export interface StagedPlanData {
  plan_id?: string
  goal?: string
  steps?: StagedPlanStep[]
  risk_level?: string
  required_approvals?: string[]
  created_at?: string
  status?: 'staged' | 'executing' | 'completed' | 'cancelled'
}

export interface MessageMetadata {
  activityTitle?: string
  audioDurationMs?: number
  interruptedAtMs?: number
  interrupted?: boolean
  plan?: StagedPlanData | Record<string, any> | null
  planStaged?: boolean
  research?: Record<string, any> | null
  heldDataApplied?: any[] | null
  [key: string]: unknown
}

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  status?: MessageStatus
  isStreaming?: boolean
  modality?: 'text' | 'voice'
  interrupted?: boolean
  metadata?: MessageMetadata
}

export interface ConversationState {
  messages: Message[]
  activeStreamingMessageId: string | null
  isStreaming: boolean
}
