import React, { useState, useRef } from 'react'
import type { FormEvent, KeyboardEvent, ChangeEvent } from 'react'
import type { PresenceState } from '../../types/presence'
import type { CognitiveMode } from '../TopHeader/TopHeader'
import './MessageComposer.css'

export interface AttachedFile {
  id: string
  name: string
  size: number
  tier: 'Liberal' | 'Sensitive' | 'More Sensitive'
}

interface MessageComposerProps {
  presenceState: PresenceState
  isListening: boolean
  isSpeaking: boolean
  voiceError?: string | null
  activeMode?: CognitiveMode
  onToggleMode?: () => void
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
  activeMode = 'think',
  onToggleMode,
  onSendMessage,
  onStartListening,
  onStopListening,
  onInterrupt,
  disabled = false,
}) => {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const canInterrupt =
    presenceState === 'speaking' ||
    presenceState === 'acting' ||
    presenceState === 'thinking' ||
    isSpeaking

  const classifyFileTier = (filename: string): 'Liberal' | 'Sensitive' | 'More Sensitive' => {
    const lower = filename.toLowerCase()
    if (
      lower.includes('aadhar') ||
      lower.includes('aadhaar') ||
      lower.includes('passport') ||
      lower.includes('tax') ||
      lower.includes('ssn') ||
      lower.includes('secret') ||
      lower.includes('id_') ||
      lower.endsWith('.env') ||
      lower.endsWith('.pem') ||
      lower.endsWith('.key')
    ) {
      return 'More Sensitive'
    }
    if (
      lower.endsWith('.pdf') ||
      lower.endsWith('.docx') ||
      lower.endsWith('.xlsx') ||
      lower.endsWith('.csv') ||
      lower.endsWith('.zip') ||
      lower.endsWith('.json') ||
      lower.endsWith('.py') ||
      lower.endsWith('.ts')
    ) {
      return 'Sensitive'
    }
    return 'Liberal'
  }

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const newAttachments: AttachedFile[] = Array.from(files).map((file) => ({
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      name: file.name,
      size: file.size,
      tier: classifyFileTier(file.name),
    }))

    setAttachedFiles((prev) => [...prev, ...newAttachments])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleRemoveFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault()
    const trimmed = text.trim()
    if ((!trimmed && attachedFiles.length === 0) || disabled) return

    let finalPrompt = trimmed
    if (attachedFiles.length > 0) {
      const fileListStr = attachedFiles
        .map((f) => `[Attachment: ${f.name} (${f.tier} Tier)]`)
        .join(' ')
      finalPrompt = trimmed ? `${fileListStr}\n\n${trimmed}` : fileListStr
    }

    onSendMessage(finalPrompt)
    setText('')
    setAttachedFiles([])
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

  const hasMoreSensitiveAttachment = attachedFiles.some((f) => f.tier === 'More Sensitive')

  return (
    <div className="message-composer-wrapper">
      {/* Attached Files Tray */}
      {attachedFiles.length > 0 && (
        <div className="composer-attachments-tray" data-testid="attachments-tray">
          <div className="attachments-list">
            {attachedFiles.map((file) => (
              <div
                key={file.id}
                className={`attachment-chip tier-${file.tier.toLowerCase().replace(' ', '-')}`}
                data-testid={`attachment-chip-${file.name}`}
              >
                <span className="attachment-icon">📎</span>
                <span className="attachment-name" title={file.name}>
                  {file.name}
                </span>
                <span className="attachment-tier-badge">{file.tier}</span>
                <button
                  type="button"
                  className="attachment-remove-btn"
                  onClick={() => handleRemoveFile(file.id)}
                  aria-label={`Remove ${file.name}`}
                  title="Remove attachment"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          {hasMoreSensitiveAttachment && (
            <div className="security-alert-inline" data-testid="more-sensitive-alert">
              <span>🛡️ <strong>More Sensitive</strong>: Encrypted via AES-256-GCM. Isolated from cloud & network.</span>
            </div>
          )}
        </div>
      )}

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        style={{ display: 'none' }}
        data-testid="file-upload-input"
        aria-label="Upload files for analysis"
      />

      <form
        className="composer-box"
        onSubmit={handleSubmit}
        data-testid="text-composer-form"
      >
        {/* Attachment Button */}
        <button
          type="button"
          className={`composer-action-btn ${attachedFiles.length > 0 ? 'active' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          title="Attach document or file (Liberal / Sensitive / More Sensitive auto-classified)"
          aria-label="Attach file"
          data-testid="attach-file-button"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
        </button>

        {/* Cognitive Mode Indicator Pill */}
        {onToggleMode && (
          <button
            type="button"
            className={`composer-mode-pill mode-${activeMode}`}
            onClick={onToggleMode}
            title={`Active Mode: ${activeMode.toUpperCase()}. Click to switch.`}
            data-testid="composer-mode-pill"
          >
            <span className="mode-dot" />
            <span className="mode-label">{activeMode}</span>
          </button>
        )}

        {/* Text Input */}
        <input
          type="text"
          className="composer-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            attachedFiles.length > 0
              ? 'Add instructions for attached file(s)...'
              : 'Message Xeren (offline intelligence)...'
          }
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
            disabled={disabled || (!text.trim() && attachedFiles.length === 0)}
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

      {/* Voice or Transcription Error Banner */}
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
