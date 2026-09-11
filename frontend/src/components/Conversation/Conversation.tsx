import React, { useEffect, useRef, useState } from 'react'
import type { Message } from '../../types/conversation'
import { MarkdownMessageView } from './MarkdownMessageView'
import './Conversation.css'

export interface ConversationProps {
  messages: Message[]
  currentStreamingText?: string
  currentStreamingId?: string | null
  onProceedPlan?: (planText?: string) => void
  onRevisePlan?: (planId?: string) => void
  onCancelPlan?: (planId?: string) => void
}

export const Conversation: React.FC<ConversationProps> = ({
  messages,
  currentStreamingText = '',
  onProceedPlan,
  onRevisePlan,
  onCancelPlan,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null)

  // Auto-scroll to bottom on new messages or streaming text
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [messages, currentStreamingText])

  const formatTime = (timestamp: number) => {
    const d = new Date(timestamp)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const handleCopyMessage = async (msgId: string, content: string) => {
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(content)
      }
      setCopiedMsgId(msgId)
      setTimeout(() => setCopiedMsgId(null), 2000)
    } catch (_) {
      // Fallback
    }
  }

  const hasMessages = messages.length > 0 || !!currentStreamingText

  return (
    <div
      className="conversation-container"
      ref={containerRef}
      aria-label="Conversation History"
      data-testid="conversation-container"
    >
      {!hasMessages ? (
        <div className="conversation-empty">
          <div className="empty-title">Natural Conversational Intelligence</div>
          <div className="empty-subtitle">
            Speak naturally with your microphone or type a query below. Xeren is ready to listen, think, and collaborate.
          </div>
        </div>
      ) : (
        <div className="message-list">
          {messages.map((msg) => {
            const isAssistant = msg.role === 'xeren' || msg.role === 'assistant'
            return (
              <div
                key={msg.id}
                className={`message-row ${msg.role} ${isAssistant ? 'assistant' : ''}`}
                data-testid={`message-row-${msg.role}`}
              >
                <div className="message-bubble">
                  {isAssistant ? (
                    <div className="message-content">
                      <MarkdownMessageView
                        content={msg.content}
                        metadata={msg.metadata}
                        onProceedPlan={onProceedPlan}
                        onRevisePlan={onRevisePlan}
                        onCancelPlan={onCancelPlan}
                      />
                    </div>
                  ) : (
                    <div className="message-content">{msg.content}</div>
                  )}

                  <div className="message-meta">
                    {msg.modality === 'voice' && (
                      <span className="message-badge" title="Voice Input">
                        🎙️ Voice
                      </span>
                    )}
                    {msg.interrupted && (
                      <span
                        className="message-badge badge-interrupted"
                        data-testid="badge-interrupted"
                      >
                        Interrupted
                      </span>
                    )}
                    <span className="message-time">{formatTime(msg.timestamp)}</span>

                    {/* Copy action icon on message */}
                    <button
                      type="button"
                      className="msg-action-copy-btn"
                      onClick={() => handleCopyMessage(msg.id, msg.content)}
                      title="Copy message text"
                      aria-label="Copy message"
                    >
                      {copiedMsgId === msg.id ? '✓' : '📋'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}

          {/* Active Streaming Assistant Bubble */}
          {currentStreamingText && (
            <div
              className="message-row assistant streaming"
              data-testid="streaming-message-row"
            >
              <div className="message-bubble">
                <div className="message-content">
                  <MarkdownMessageView
                    content={currentStreamingText}
                    isStreaming={true}
                  />
                  <span className="streaming-cursor" data-testid="streaming-cursor" />
                </div>
                <div className="message-meta">
                  <span className="message-badge">Generating...</span>
                  <span className="message-time">Just now</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Conversation
