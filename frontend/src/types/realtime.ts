/**
 * Typed real-time communication events between Xeren frontend and backend.
 */

export type ConnectionState =
  | 'connected'
  | 'connecting'
  | 'reconnecting'
  | 'offline'
  | 'error'

export type ClientEventType =
  | 'conversation.start'
  | 'conversation.item.create'
  | 'user.text'
  | 'user.audio.start'
  | 'user.audio.chunk'
  | 'user.audio.end'
  | 'response.create'
  | 'response.cancel'

export interface ClientEventBase {
  type: ClientEventType
  timestamp: number
  sessionId?: string
}

export interface ConversationStartClientEvent extends ClientEventBase {
  type: 'conversation.start'
  metadata?: Record<string, unknown>
}

export interface ConversationItemCreateClientEvent extends ClientEventBase {
  type: 'conversation.item.create'
  item?: {
    role: string
    content: Array<{ type: string; text?: string }>
  }
}

export interface UserTextClientEvent extends ClientEventBase {
  type: 'user.text'
  text: string
}

export interface UserAudioStartClientEvent extends ClientEventBase {
  type: 'user.audio.start'
  sampleRate?: number
}

export interface UserAudioChunkClientEvent extends ClientEventBase {
  type: 'user.audio.chunk'
  audioBase64: string
}

export interface UserAudioEndClientEvent extends ClientEventBase {
  type: 'user.audio.end'
}

export interface ResponseCreateClientEvent extends ClientEventBase {
  type: 'response.create'
  response?: {
    modalities?: string[]
  }
}

export interface ResponseCancelClientEvent extends ClientEventBase {
  type: 'response.cancel'
  reason?: string
}

export type ClientEvent =
  | ConversationStartClientEvent
  | ConversationItemCreateClientEvent
  | UserTextClientEvent
  | UserAudioStartClientEvent
  | UserAudioChunkClientEvent
  | UserAudioEndClientEvent
  | ResponseCreateClientEvent
  | ResponseCancelClientEvent

export type ServerEventType =
  | 'response.created'
  | 'response.text.delta'
  | 'response.text.complete'
  | 'response.text.done'
  | 'response.audio.start'
  | 'response.audio.chunk'
  | 'response.audio.end'
  | 'response.done'
  | 'agent.status'
  | 'task.status'
  | 'error'

export interface ServerEventBase {
  type: ServerEventType
  timestamp: number
  sessionId?: string
}

export interface ResponseCreatedServerEvent extends ServerEventBase {
  type: 'response.created'
  response: {
    id: string
    [key: string]: unknown
  }
}

export interface ResponseTextDeltaServerEvent extends ServerEventBase {
  type: 'response.text.delta'
  delta: string
  messageId?: string
}

export interface ResponseTextCompleteServerEvent extends ServerEventBase {
  type: 'response.text.complete' | 'response.text.done'
  text: string
  messageId?: string
  response_id?: string
  plan?: Record<string, any> | null
  plan_staged?: boolean
  research?: Record<string, any> | null
  held_data_applied?: any[] | null
}

export interface ResponseAudioStartServerEvent extends ServerEventBase {
  type: 'response.audio.start'
  messageId?: string
  mimeType?: string
}

export interface ResponseAudioChunkServerEvent extends ServerEventBase {
  type: 'response.audio.chunk'
  messageId?: string
  audioBase64: string
}

export interface ResponseAudioEndServerEvent extends ServerEventBase {
  type: 'response.audio.end'
  messageId?: string
}

export interface ResponseDoneServerEvent extends ServerEventBase {
  type: 'response.done'
}

export interface AgentStatusServerEvent extends ServerEventBase {
  type: 'agent.status'
  phase?: 'understanding' | 'planning' | 'researching' | 'creating' | 'verifying' | 'completed'
  activityTitle?: string
  progressPercent?: number
  status?: string
  details?: {
    phase?: 'understanding' | 'planning' | 'researching' | 'creating' | 'verifying' | 'completed'
    goal?: string
    milestone?: 'understanding' | 'planning' | 'researching' | 'creating' | 'verifying' | 'completed'
    progress_percent?: number
    action_type?: string
    active_tool?: string
  }
}

export interface TaskStatusServerEvent extends ServerEventBase {
  type: 'task.status'
  taskId: string
  status: 'pending' | 'running' | 'waiting_approval' | 'completed' | 'failed'
  details?: Record<string, unknown>
}

export interface ErrorServerEvent extends ServerEventBase {
  type: 'error'
  code: string
  message: string
  recoverable: boolean
}

export type ServerEvent =
  | ResponseCreatedServerEvent
  | ResponseTextDeltaServerEvent
  | ResponseTextCompleteServerEvent
  | ResponseAudioStartServerEvent
  | ResponseAudioChunkServerEvent
  | ResponseAudioEndServerEvent
  | ResponseDoneServerEvent
  | AgentStatusServerEvent
  | TaskStatusServerEvent
  | ErrorServerEvent
