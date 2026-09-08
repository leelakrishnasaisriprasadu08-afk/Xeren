/**
 * Message and transcript schema definitions.
 */

export type MessageRole = 'user' | 'xeren' | 'assistant' | 'system'

export type MessageStatus = 'streaming' | 'complete' | 'error' | 'interrupted'

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  status?: MessageStatus
  isStreaming?: boolean
  modality?: 'text' | 'voice'
  interrupted?: boolean
  metadata?: {
    activityTitle?: string
    audioDurationMs?: number
    interruptedAtMs?: number
    interrupted?: boolean
    [key: string]: unknown
  }
}

export interface ConversationState {
  messages: Message[]
  activeStreamingMessageId: string | null
  isStreaming: boolean
}
