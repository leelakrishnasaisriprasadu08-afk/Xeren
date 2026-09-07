import React, { useState } from 'react'
import type { ConnectionState } from '../../types/realtime'
import { ConnectionStatus } from '../ConnectionStatus/ConnectionStatus'
import './TopHeader.css'

interface TopHeaderProps {
  connectionState: ConnectionState
  transportType: string
  onReconnect?: () => void
  onOpenSettings: () => void
  onToggleSidebar?: () => void
  onToggleRightPanel?: () => void
  onViewLanding?: () => void
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  connectionState,
  transportType,
  onReconnect,
  onOpenSettings,
  onToggleSidebar,
  onToggleRightPanel,
  onViewLanding,
}) => {
  const [activeTab, setActiveTab] = useState<'think' | 'reason' | 'create'>('think')

  return (
    <header className="top-header" role="banner" data-testid="top-header">
      {/* Left: Mobile Toggle + Logo + Nav */}
      <div className="header-left">
        {onToggleSidebar && (
          <button
            type="button"
            className="mobile-toggle-btn"
            onClick={onToggleSidebar}
            aria-label="Toggle navigation menu"
            data-testid="toggle-sidebar-btn"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        )}

        <div className="brand-block">
          {/* Stylized Hexagonal Xeren Icon */}
          <div className="brand-icon" aria-hidden="true">
            <svg width="26" height="26" viewBox="0 0 32 32" fill="none">
              <polygon
                points="16,3 28,10 28,22 16,29 4,22 4,10"
                stroke="url(#headerLogoGrad)"
                strokeWidth="2"
                fill="rgba(0, 240, 255, 0.08)"
              />
              <path
                d="M11 11 L16 16 L11 21 M21 11 L16 16 L21 21"
                stroke="#ffffff"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <defs>
                <linearGradient id="headerLogoGrad" x1="0" y1="0" x2="32" y2="32">
                  <stop stopColor="#00f0ff" />
                  <stop offset="1" stopColor="#a855f7" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 className="brand-text">XEREN</h1>
        </div>

        {/* Navigation Tabs: Think / Reason / Create */}
        <nav className="header-nav" aria-label="Main Navigation Tabs">
          <button
            type="button"
            className={`header-nav-tab ${activeTab === 'think' ? 'active' : ''}`}
            onClick={() => setActiveTab('think')}
          >
            Think
          </button>
          <button
            type="button"
            className={`header-nav-tab ${activeTab === 'reason' ? 'active' : ''}`}
            onClick={() => setActiveTab('reason')}
          >
            Reason
          </button>
          <button
            type="button"
            className={`header-nav-tab ${activeTab === 'create' ? 'active' : ''}`}
            onClick={() => setActiveTab('create')}
          >
            Create
          </button>
        </nav>
      </div>

      {/* Right: System Ready + Status Pill + Notification + User */}
      <div className="header-right">
        {/* System Ready indicator */}
        <div className="system-ready-pill" title="Xeren Runtime Operational">
          <span className="ready-dot" />
          <span>System Ready</span>
        </div>

        {/* 1.0 Presence status pill */}
        <span className="version-badge">1.0 Presence</span>

        {/* Connection status (Live / Mock) */}
        <ConnectionStatus
          state={connectionState}
          transportType={transportType}
          onReconnect={onReconnect}
        />

        {/* Landing Page Link */}
        {onViewLanding && (
          <button
            type="button"
            className="landing-view-btn"
            onClick={onViewLanding}
            title="View HLS Video Landing Page"
            aria-label="View Landing Page"
            data-testid="header-landing-btn"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span>Landing</span>
          </button>
        )}

        {/* Notification Bell */}
        <button
          type="button"
          className="icon-button"
          aria-label="Notifications"
          title="Notifications"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span className="notification-dot" />
        </button>

        {/* Settings / Profile Button */}
        <button
          type="button"
          className="user-avatar-button"
          onClick={onOpenSettings}
          aria-label="Open Settings"
          title="Settings and Configuration"
          data-testid="settings-button"
        >
          XR
        </button>

        {/* Right Panel Toggle (for smaller screens) */}
        {onToggleRightPanel && (
          <button
            type="button"
            className="mobile-toggle-btn"
            onClick={onToggleRightPanel}
            aria-label="Toggle system panel"
            data-testid="toggle-right-panel-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <line x1="15" y1="3" x2="15" y2="21" />
            </svg>
          </button>
        )}
      </div>
    </header>
  )
}
