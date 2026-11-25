import React, { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import './TextComposer.css'

interface TextComposerProps {
  onSendMessage: (text: string) => void
  disabled?: boolean
  placeholder?: string
}

export const TextComposer: React.FC<TextComposerProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = 'Speak or type a message to Xeren...',
}) => {
  const [text, setText] = useState('')

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

  return (
    <form
      className="text-composer-form"
      onSubmit={handleSubmit}
      data-testid="text-composer-form"
    >
      <input
        type="text"
        className="text-composer-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        aria-label="Message input"
        data-testid="text-composer-input"
      />
      <button
        type="submit"
        className="send-button"
        disabled={disabled || !text.trim()}
        aria-label="Send message"
        data-testid="send-message-button"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </form>
  )
}
