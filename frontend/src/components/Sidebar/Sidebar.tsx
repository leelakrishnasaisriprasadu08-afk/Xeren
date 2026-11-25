import React, { useState } from 'react'
import './Sidebar.css'

export interface SidebarProps {
  isOpen: boolean
  onClose?: () => void
  onToggle?: () => void
  onOpenSettings: () => void
  onSelectNav?: (navId: string) => void
  onNewChat?: () => void
  onOpenNewProject?: () => void
  onOpenPlugins?: () => void
  onOpenApps?: () => void
  onOpenKnowledge?: () => void
  onOpenProjects?: () => void
  onOpenRelay?: () => void
  activeProjectName?: string
  currentUserHandle?: string
}

interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  badge?: string
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onToggle,
  onOpenSettings,
  onSelectNav,
  onNewChat,
  onOpenNewProject,
  onOpenPlugins,
  onOpenApps,
  onOpenKnowledge,
  onOpenProjects,
  onOpenRelay,
  activeProjectName,
}) => {
  const [activeItem, setActiveItem] = useState('home')

  const navItems: NavItem[] = [
    {
      id: 'home',
      label: 'Home',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      ),
    },
    {
      id: 'chat',
      label: 'Chat',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
    },
    {
      id: 'web-agent',
      label: 'Connected Apps',
      badge: 'Beta',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      ),
    },
    {
      id: 'plugins',
      label: 'Plugins',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
      ),
    },
    {
      id: 'knowledge',
      label: 'Knowledge Vault',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
      ),
    },
    {
      id: 'projects',
      label: 'Projects',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      ),
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      ),
    },
  ]

  const handleItemClick = (id: string) => {
    setActiveItem(id)
    if (id === 'settings') {
      onOpenSettings()
    } else if (id === 'relay') {
      onOpenRelay ? onOpenRelay() : onOpenProjects ? onOpenProjects() : onSelectNav?.(id)
    } else if (id === 'plugins') {
      onOpenPlugins ? onOpenPlugins() : onSelectNav?.(id)
    } else if (id === 'web-agent') {
      onOpenApps ? onOpenApps() : onSelectNav?.(id)
    } else if (id === 'knowledge') {
      onOpenKnowledge ? onOpenKnowledge() : onSelectNav?.(id)
    } else if (id === 'projects') {
      onOpenProjects ? onOpenProjects() : onSelectNav?.(id)
    } else {
      onSelectNav?.(id)
    }

    if (window.innerWidth <= 900) {
      onClose?.()
    }
  }

  const handleNewChatClick = () => {
    setActiveItem('chat')
    onNewChat?.()
    onSelectNav?.('new-chat')
    if (window.innerWidth <= 900) {
      onClose?.()
    }
  }

  const handleNewProjectClick = () => {
    onOpenNewProject?.()
    onSelectNav?.('new-project')
    if (window.innerWidth <= 900) {
      onClose?.()
    }
  }

  return (
    <aside
      className={`left-sidebar ${isOpen ? 'open' : ''}`}
      aria-label="Application Navigation"
      data-testid="left-sidebar"
    >
      <div className="sidebar-top-bar">
        <div className="sidebar-brand-group">
          <span className="sidebar-brand-gem">❖</span>
          <span className="sidebar-brand-name">WORKSPACE</span>
        </div>
        <button
          type="button"
          className="sidebar-collapse-trigger"
          onClick={onToggle || onClose}
          title="Collapse sidebar"
          aria-label="Collapse sidebar"
          data-testid="sidebar-collapse-btn"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>

      {/* Primary Action Buttons */}
      <div className="sidebar-primary-actions">
        <button
          type="button"
          className="sidebar-action-btn primary"
          onClick={handleNewChatClick}
          data-testid="sidebar-new-chat-btn"
          title="Start new reasoning session"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>New Chat</span>
        </button>
        <button
          type="button"
          className="sidebar-action-btn secondary"
          onClick={handleNewProjectClick}
          data-testid="sidebar-new-project-btn"
          title="Create a new collaborative project"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <line x1="12" y1="11" x2="12" y2="17" />
            <line x1="9" y1="14" x2="15" y2="14" />
          </svg>
          <span>New Project</span>
        </button>
      </div>

      {/* Scrollable Navigation Area */}
      <div className="sidebar-scroll-area">
        <nav className="sidebar-nav-list" role="navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`sidebar-nav-item ${activeItem === item.id ? 'active' : ''}`}
              onClick={() => handleItemClick(item.id)}
              data-testid={`nav-item-${item.id}`}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span className="nav-label">{item.label}</span>
              {item.badge && <span className="beta-badge">{item.badge}</span>}
            </button>
          ))}
        </nav>

        {/* Active Projects Section */}
        <div className="sidebar-section">
          <div className="section-header">
            <span className="section-title">ACTIVE WORKSPACE</span>
            <button
              type="button"
              className="section-action-btn"
              onClick={handleNewProjectClick}
              aria-label="Create new project"
              title="Add project"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
          </div>
          <button
            type="button"
            className="active-project-card active-relay-card"
            onClick={() => handleItemClick('relay')}
            title={`Open Xeren Relay Autonomous Workspace${activeProjectName ? ` (${activeProjectName})` : ''}`}
            data-testid="sidebar-active-relay-btn"
            data-active-project={activeProjectName}
          >
            <span className="active-project-dot relay-pulse" />
            <div className="active-project-info">
              <span className="active-project-name text-truncate">
                Xeren Relay
              </span>
              <span className="active-project-tag">Autonomous Relay Workspace</span>
            </div>
            <span className="active-project-arrow">→</span>
          </button>
        </div>

        {/* Bottom promotional / info card */}
        <div className="sidebar-promo-card">
          <div className="promo-glow" aria-hidden="true" />
          <div className="promo-title">Build. Automate. Grow.</div>
          <div className="promo-text">
            Continuous AI intelligence across reasoning, creation and web execution.
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
