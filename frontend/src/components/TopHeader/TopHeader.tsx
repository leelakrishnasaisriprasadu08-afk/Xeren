import type { ConnectionState } from '../../types/realtime'
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
  unreadNotificationsCount = 0,
  onOpenNotifications,
  onOpenAuth,
  activeProjectName,
  onOpenProjectWorkspace,
  currentUserHandle = '@xeren_dev',
  currentUserAvatar,
  onOpenSettings,
  onToggleSidebar,
  onToggleRightPanel,
  onViewLanding,
  onGoHome,
}) => {
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
                fill="rgba(16, 185, 129, 0.08)"
              />
              <path
                d="M11 11 L16 16 L11 21 M21 11 L16 16 L21 21"
                stroke="#f8fafc"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <defs>
                <linearGradient id="headerLogoGrad" x1="0" y1="0" x2="32" y2="32">
                  <stop stopColor="#10b981" />
                  <stop offset="1" stopColor="#047857" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 className="brand-text">XEREN</h1>
        </div>

        {activeProjectName && (
          <button
            type="button"
            className="header-active-project-btn"
            onClick={onOpenProjectWorkspace}
            title="Open Dedicated Collaborative Project Workspace"
            data-testid="header-active-project-btn"
          >
            <span className="project-icon">⚡</span>
            <span className="project-name">{activeProjectName}</span>
            <span className="project-tag">Coach</span>
          </button>
        )}
      </div>

      {/* Right: User and Notifications Only */}
      <div className="header-right">
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

