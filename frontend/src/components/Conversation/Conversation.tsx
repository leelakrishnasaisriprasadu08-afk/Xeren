import React, { useEffect, useRef } from 'react'
import type { Message } from '../../types/conversation'
import './Conversation.css'

interface ConversationProps {
  messages: Message[]
  currentStreamingText?: string
  currentStreamingId?: string | null
}

export const Conversation: React.FC<ConversationProps> = ({
  messages,
  currentStreamingText = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null)

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
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`message-row ${msg.role}`}
              data-testid={`message-row-${msg.role}`}
            >
              <div className="message-bubble">
                <div className="message-content">{msg.content}</div>
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
                </div>
              </div>
            </div>
          ))}

          {/* Active Streaming Assistant Bubble */}
          {currentStreamingText && (
            <div
              className="message-row assistant streaming"
              data-testid="streaming-message-row"
            >
              <div className="message-bubble">
                <div className="message-content">
                  {currentStreamingText}
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
