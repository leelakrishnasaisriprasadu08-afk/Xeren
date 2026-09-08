import React, { useState } from 'react'
import type { ConnectionState } from '../../types/realtime'
import { ConnectionStatus } from '../ConnectionStatus/ConnectionStatus'
import './TopHeader.css'

export type CognitiveMode = 'think' | 'reason' | 'create'

interface TopHeaderProps {
  connectionState: ConnectionState
  transportType: string
  activeMode?: CognitiveMode
  onSelectMode?: (mode: CognitiveMode) => void
  unreadNotificationsCount?: number
  onOpenNotifications?: () => void
  onOpenPlugins?: () => void
  onOpenKnowledge?: () => void
  onOpenConnectedApps?: () => void
  onOpenNewProject?: () => void
  onOpenAuth?: () => void
  activeProjectName?: string
  onOpenProjectWorkspace?: () => void
  currentUserHandle?: string
  currentUserAvatar?: string
  dbConnected?: boolean
  dbMode?: string
  systemVersion?: string
  adaptiveScore?: number
  onOpenImprovementHub?: () => void
  onReconnect?: () => void
  onOpenSettings: () => void
  onToggleSidebar?: () => void
  onToggleRightPanel?: () => void
  onViewLanding?: () => void
  onGoHome?: () => void
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  connectionState,
  transportType,
  activeMode,
  onSelectMode,
  unreadNotificationsCount = 0,
  onOpenNotifications,
  onOpenPlugins,
  onOpenKnowledge,
  onOpenConnectedApps,
  onOpenNewProject,
  onOpenAuth,
  activeProjectName,
  onOpenProjectWorkspace,
  currentUserHandle = '@xeren_dev',
  currentUserAvatar,
  dbConnected = false,
  dbMode = 'local',
  systemVersion = 'v1.2.0',
  adaptiveScore = 94.8,
  onOpenImprovementHub,
  onReconnect,
  onOpenSettings,
  onToggleSidebar,
  onToggleRightPanel,
  onViewLanding,
  onGoHome,
}) => {
  const [localTab, setLocalTab] = useState<CognitiveMode>('think')
  const currentMode = activeMode ?? localTab

  const handleTabClick = (mode: CognitiveMode) => {
    setLocalTab(mode)
    onSelectMode?.(mode)
  }

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

        <div
          className="brand-block clickable"
          onClick={onGoHome}
          role="button"
          tabIndex={0}
          title="Xeren Autonomous Workstation Home"
        >
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
            className={`header-nav-tab ${currentMode === 'think' ? 'active' : ''}`}
            onClick={() => handleTabClick('think')}
            title="Deep Chain-of-Thought & Strawberry Multi-Angle Research Mode"
            data-testid="mode-tab-think"
          >
            Think
          </button>
          <button
            type="button"
            className={`header-nav-tab ${currentMode === 'reason' ? 'active' : ''}`}
            onClick={() => handleTabClick('reason')}
            title="Fast Autonomous Problem Solving & Tool Routing Mode"
            data-testid="mode-tab-reason"
          >
            Reason
          </button>
          <button
            type="button"
            className={`header-nav-tab ${currentMode === 'create' ? 'active' : ''}`}
            onClick={() => handleTabClick('create')}
            title="Web, Code Synthesis & Freelance Deliverable Packaging Mode"
            data-testid="mode-tab-create"
          >
            Create
          </button>
        </nav>

        {/* New Project Button */}
        {onOpenNewProject && (
          <button
            type="button"
            className="header-new-project-btn"
            onClick={onOpenNewProject}
            title="Start Solo or Collaborative Group Project"
            aria-label="Start New Project"
            data-testid="header-new-project-btn"
          >
            <span className="btn-plus">+</span>
            <span>New Project</span>
          </button>
        )}

        {/* Active Project Workspace & AI Coach Button */}
        {onOpenProjectWorkspace && (
          <button
            type="button"
            className="header-active-project-btn"
            onClick={onOpenProjectWorkspace}
            title="Open Dedicated Project Workspace & AI Coach"
            aria-label="Open Project Workspace"
            data-testid="header-active-project-btn"
          >
            <span className="project-folder-icon">📁</span>
            <span className="project-btn-name">{activeProjectName || 'CyberForge AI Engine'}</span>
            <span className="coach-badge-mini">Coach</span>
          </button>
        )}
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

        {/* Neural Learning & LLM Self-Improvement Pill */}
        <button
          type="button"
          className="adaptive-intelligence-pill"
          onClick={onOpenImprovementHub}
          title="Neural Learning Active • View Distilled Query Patterns & Evolved Directives"
          data-testid="header-adaptive-pill"
        >
          <span style={{ fontSize: '0.85rem' }}>🧠</span>
          <span>{adaptiveScore ? `${adaptiveScore.toFixed(1)}%` : '94.8%'} Adaptive</span>
        </button>

        {/* System Version & MongoDB Handshake pill */}
        <div
          className={`system-version-pill ${dbConnected ? 'db-online' : 'db-local'}`}
          title={`Backend ${systemVersion} • MongoDB Mode: ${dbMode}`}
          data-testid="header-system-version-pill"
        >
          <span className={`db-status-dot ${dbConnected ? 'online' : 'local'}`} />
          <span className="version-txt">{systemVersion}</span>
          <span className="db-sub-tag">{dbConnected ? 'Atlas' : 'Local DB'}</span>
        </div>

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

        {/* Plugins Quick Trigger */}
        {onOpenPlugins && (
          <button
            type="button"
            className="header-pill-btn"
            onClick={onOpenPlugins}
            title="Autonomous Plugins Registry"
            aria-label="Open Plugins"
            data-testid="header-plugins-btn"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            <span>Plugins</span>
          </button>
        )}

        {/* Knowledge Vault Quick Trigger */}
        {onOpenKnowledge && (
          <button
            type="button"
            className="header-pill-btn"
            onClick={onOpenKnowledge}
            title="Local Qdrant Knowledge Vault"
            aria-label="Open Knowledge Vault"
            data-testid="header-knowledge-btn"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span>Vault</span>
          </button>
        )}

        {/* Connected Apps & MCP Quick Trigger */}
        {onOpenConnectedApps && (
          <button
            type="button"
            className="header-pill-btn"
            onClick={onOpenConnectedApps}
            title="Connected Apps & MCP Hub"
            aria-label="Open Connected Apps"
            data-testid="header-apps-btn"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
            <span>Apps</span>
          </button>
        )}

        {/* Interactive Notification Bell */}
        <button
          type="button"
          className={`icon-button notif-bell-btn ${unreadNotificationsCount > 0 ? 'has-unread' : ''}`}
          onClick={onOpenNotifications}
          aria-label={`Notifications (${unreadNotificationsCount} unread)`}
          title="Open Activity & Notifications Center"
          data-testid="header-notifications-btn"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          {unreadNotificationsCount > 0 ? (
            <span className="notification-counter" data-testid="header-unread-count">
              {unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount}
            </span>
          ) : (
            <span className="notification-dot quiet" />
          )}
        </button>

        {/* User Profile & Authentication Dashboard Trigger */}
        {onOpenAuth && (
          <button
            type="button"
            className="header-user-profile-btn"
            onClick={onOpenAuth}
            aria-label="Open User Authentication Dashboard"
            title={`Logged in as ${currentUserHandle}`}
            data-testid="header-user-profile-btn"
          >
            {currentUserAvatar ? (
              <img src={currentUserAvatar} alt="User avatar" className="header-avatar-img" />
            ) : (
              <span className="header-avatar-initials">
                {currentUserHandle ? currentUserHandle.slice(1, 3).toUpperCase() : 'XR'}
              </span>
            )}
            <span className="header-user-handle">{currentUserHandle}</span>
          </button>
        )}

        {/* Settings / System Menu Button */}
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

