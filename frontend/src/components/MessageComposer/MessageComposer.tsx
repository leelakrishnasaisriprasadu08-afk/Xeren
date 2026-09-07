import React, { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import type { PresenceState } from '../../types/presence'
import './MessageComposer.css'

interface MessageComposerProps {
  presenceState: PresenceState
  isListening: boolean
  isSpeaking: boolean
  voiceError?: string | null
  onSendMessage: (text: string) => void
  onStartListening: () => void
  onStopListening: () => void
  onInterrupt: () => void
  disabled?: boolean
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  presenceState,
  isListening,
  isSpeaking,
  voiceError,
  onSendMessage,
  onStartListening,
  onStopListening,
  onInterrupt,
  disabled = false,
}) => {
  const [text, setText] = useState('')

  const canInterrupt =
    presenceState === 'speaking' ||
    presenceState === 'acting' ||
    presenceState === 'thinking' ||
    isSpeaking

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSendMessage(trimmed)
    setText('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleMicClick = () => {
    if (isListening) {
      onStopListening()
    } else {
      onStartListening()
    }
  }

  return (
    <div className="message-composer-wrapper">
      <form
        className="composer-box"
        onSubmit={handleSubmit}
        data-testid="text-composer-form"
      >
        {/* Attachment Button */}
        <button
          type="button"
          className="composer-action-btn"
          title="Attach file or context"
          aria-label="Attach file"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
        </button>

        {/* Text Input */}
        <input
          type="text"
          className="composer-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Xeren..."
          disabled={disabled}
          aria-label="Message input"
          data-testid="text-composer-input"
        />

        {/* Right Actions: Interrupt / Mic / Send */}
        <div className="composer-right-actions">
          {canInterrupt && (
            <button
              type="button"
              className="composer-interrupt-btn"
              onClick={onInterrupt}
              aria-label="Interrupt Xeren"
              data-testid="interrupt-button"
            >
              <span>Stop</span>
              <kbd>Esc</kbd>
            </button>
          )}

          {/* Microphone button */}
          <button
            type="button"
            className={`composer-mic-btn ${isListening ? 'listening' : ''}`}
            onClick={handleMicClick}
            aria-label={isListening ? 'Stop listening' : 'Start speaking with Xeren'}
            title={isListening ? 'Stop listening' : 'Speak to Xeren'}
            data-testid="mic-button"
          >
            {isListening ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.5">
                <rect x="6" y="6" width="12" height="12" rx="2" fill="#38bdf8" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            )}
          </button>

          {/* Send button */}
          <button
            type="submit"
            className="composer-send-btn"
            disabled={disabled || !text.trim()}
            aria-label="Send message"
            data-testid="send-message-button"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </form>

      {/* Friendly error banner if microphone access fails */}
      {voiceError && (
        <div
          className="composer-error-banner"
          role="alert"
          data-testid="voice-error-banner"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{voiceError}</span>
        </div>
      )}
    </div>
  )
}
