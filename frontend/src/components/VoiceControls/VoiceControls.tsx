import React from 'react'
import type { PresenceState } from '../../types/presence'
import './VoiceControls.css'

interface VoiceControlsProps {
  presenceState: PresenceState
  isListening: boolean
  isSpeaking: boolean
  errorMessage?: string | null
  onStartListening: () => void
  onStopListening: () => void
  onInterrupt: () => void
}

export const VoiceControls: React.FC<VoiceControlsProps> = ({
  presenceState,
  isListening,
  isSpeaking,
  errorMessage,
  onStartListening,
  onStopListening,
  onInterrupt,
}) => {
  const canInterrupt =
    presenceState === 'speaking' ||
    presenceState === 'acting' ||
    presenceState === 'thinking' ||
    isSpeaking

  const handleMicClick = () => {
    if (isListening) {
      onStopListening()
    } else {
      onStartListening()
    }
  }

  return (
    <div className="voice-controls-container" data-testid="voice-controls-container">
      <div className="voice-controls-row">
        {/* Barge-in / Interrupt Button when Xeren is speaking or acting */}
        {canInterrupt && (
          <button
            type="button"
            className="interrupt-button"
            onClick={onInterrupt}
            aria-label="Interrupt Xeren"
            data-testid="interrupt-button"
          >
            <span>Interrupt</span>
            <kbd>Esc</kbd>
          </button>
        )}

        {/* Primary Mic Button */}
        <button
          type="button"
          className={`mic-button ${isListening ? 'listening' : ''}`}
          onClick={handleMicClick}
          aria-label={isListening ? 'Stop listening' : 'Start speaking with Xeren'}
          data-testid="mic-button"
        >
          {isListening ? (
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="6" y="6" width="12" height="12" rx="2" fill="#38bdf8" />
            </svg>
          ) : (
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          )}
        </button>
      </div>

      {/* Friendly error banner if microphone access fails */}
      {errorMessage && (
        <div
          className="voice-error-banner"
          role="alert"
          data-testid="voice-error-banner"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Voice Hint */}
      {!errorMessage && (
        <div className="voice-hint">
          {isListening ? 'Listening to your voice...' : 'Press space or click to speak'}
        </div>
      )}
    </div>
  )
}
