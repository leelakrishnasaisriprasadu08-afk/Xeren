import React, { useEffect } from 'react'
import type { TransportType } from '../../hooks/useRealtimeConnection'
import './MoreMenu.css'

interface MoreMenuProps {
  isOpen: boolean
  onClose: () => void
  transportType: TransportType
  onSwitchTransport: (type: TransportType) => void
  isVoiceOutputEnabled: boolean
  onToggleVoiceOutput: (enabled: boolean) => void
  isReducedMotion: boolean
  onToggleReducedMotion: (val: boolean | null) => void
  onClearHistory: () => void
}

export const MoreMenu: React.FC<MoreMenuProps> = ({
  isOpen,
  onClose,
  transportType,
  onSwitchTransport,
  isVoiceOutputEnabled,
  onToggleVoiceOutput,
  isReducedMotion,
  onToggleReducedMotion,
  onClearHistory,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="more-menu-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Settings and Options"
      data-testid="more-menu-backdrop"
    >
      <div
        className="more-menu-panel"
        onClick={(e) => e.stopPropagation()}
        data-testid="more-menu-panel"
      >
        <div className="menu-header">
          <div className="menu-title">Settings & System</div>
          <button
            type="button"
            className="menu-close-button"
            onClick={onClose}
            aria-label="Close Settings"
            data-testid="close-menu-button"
          >
            ✕
          </button>
        </div>

        {/* Real-time Gateway Transport */}
        <div className="menu-section">
          <span className="section-label">Realtime Connection</span>
          <div className="menu-row">
            <span className="menu-row-label">Transport Mode</span>
            <select
              className="menu-select"
              value={transportType}
              onChange={(e) => onSwitchTransport(e.target.value as TransportType)}
              data-testid="transport-select"
            >
              <option value="mock">Mock Mode (Dev/Offline)</option>
              <option value="websocket">WebSocket Gateway</option>
            </select>
          </div>
        </div>

        {/* Audio Synthesis Toggle */}
        <div className="menu-section">
          <span className="section-label">Audio & Voice</span>
          <div className="menu-row">
            <span className="menu-row-label">Voice Synthesis</span>
            <select
              className="menu-select"
              value={isVoiceOutputEnabled ? 'true' : 'false'}
              onChange={(e) => onToggleVoiceOutput(e.target.value === 'true')}
              data-testid="voice-output-select"
            >
              <option value="true">Enabled</option>
              <option value="false">Muted (Text Only)</option>
            </select>
          </div>
        </div>

        {/* Accessibility: Motion */}
        <div className="menu-section">
          <span className="section-label">Accessibility</span>
          <div className="menu-row">
            <span className="menu-row-label">Reduced Motion</span>
            <select
              className="menu-select"
              value={isReducedMotion ? 'reduce' : 'allow'}
              onChange={(e) => onToggleReducedMotion(e.target.value === 'reduce')}
              data-testid="reduced-motion-select"
            >
              <option value="allow">Full Animations</option>
              <option value="reduce">Reduced Motion</option>
            </select>
          </div>
        </div>

        {/* Session Management */}
        <div className="menu-section">
          <span className="section-label">Session</span>
          <button
            type="button"
            className="menu-button danger"
            onClick={() => {
              onClearHistory()
              onClose()
            }}
            data-testid="clear-history-button"
          >
            Clear Conversation
          </button>
        </div>

        {/* Keyboard Shortcuts Reference */}
        <div className="menu-section">
          <span className="section-label">Keyboard Shortcuts</span>
          <div className="shortcut-list">
            <div className="shortcut-item">
              <span>Toggle Voice / Speak</span>
              <kbd>Space / M</kbd>
            </div>
            <div className="shortcut-item">
              <span>Barge-in / Interrupt</span>
              <kbd>Esc</kbd>
            </div>
            <div className="shortcut-item">
              <span>Send typed message</span>
              <kbd>Enter</kbd>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
