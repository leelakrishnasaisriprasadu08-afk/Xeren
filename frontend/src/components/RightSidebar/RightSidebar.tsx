import React from 'react'
import type { ConnectionState } from '../../types/realtime'
import './RightSidebar.css'

interface RightSidebarProps {
  isOpen: boolean
  transportType: string
  connectionState: ConnectionState
  onSelectPrompt: (prompt: string) => void
  onClose?: () => void
}

export const RightSidebar: React.FC<RightSidebarProps> = ({
  isOpen,
  transportType,
  connectionState,
  onSelectPrompt,
}) => {
  const isMock = transportType === 'mock'
  const isConnected = connectionState === 'connected'

  const quickActions = [
    {
      id: 'create-site',
      label: 'Create Website',
      prompt: 'Create a modern, responsive website with interactive components',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      ),
    },
    {
      id: 'research-topic',
      label: 'Research Topic',
      prompt: 'Research the latest research papers and benchmarks on AI agents',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      ),
    },
    {
      id: 'use-plugins',
      label: 'Use Plugins',
      prompt: 'Activate plugins for coding, research, and data workflows',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      ),
    },
    {
      id: 'view-projects',
      label: 'View Projects',
      prompt: 'Summarize the active project status, files, and tasks',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      ),
    },
  ]

  // Actual status values based on real frontend & connection state
  const systemItems = [
    {
      name: 'Core Model',
      status: isMock ? 'Simulated' : isConnected ? 'Gateway Connected' : 'Offline',
      type: isMock ? 'simulated' : isConnected ? 'active' : 'offline',
    },
    {
      name: 'RAG System',
      status: isMock ? 'Simulated' : isConnected ? 'Gateway Connected' : 'Offline',
      type: isMock ? 'simulated' : isConnected ? 'active' : 'offline',
    },
    {
      name: 'Plugin Manager',
      status: isMock ? 'Active (5 Plugins)' : isConnected ? 'Active' : 'Offline',
      type: isConnected || isMock ? 'active' : 'offline',
    },
    {
      name: 'Browser Agent',
      status: isMock ? 'Ready (Mock)' : isConnected ? 'Connected' : 'Offline',
      type: isMock ? 'simulated' : isConnected ? 'active' : 'offline',
    },
    {
      name: 'Database',
      status: isMock ? 'Local / In-Memory' : isConnected ? 'Connected' : 'Offline',
      type: isConnected || isMock ? 'active' : 'offline',
    },
  ]

  return (
    <aside
      className={`right-sidebar ${isOpen ? 'open' : ''}`}
      aria-label="Quick actions and system status"
      data-testid="right-sidebar"
    >
      {/* Quick Actions Section */}
      <div className="right-section">
        <div className="right-section-title">
          <span>Quick Actions</span>
        </div>
        <div className="quick-actions-list">
          {quickActions.map((action) => (
            <button
              key={action.id}
              type="button"
              className="quick-action-btn"
              onClick={() => onSelectPrompt(action.prompt)}
              data-testid={`quick-action-${action.id}`}
            >
              <span className="quick-action-icon" aria-hidden="true">
                {action.icon}
              </span>
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* System Status Section */}
      <div className="right-section">
        <div className="right-section-title">
          <span>System Status</span>
        </div>
        <div className="system-status-card" data-testid="system-status-card">
          {isMock && (
            <div className="mode-callout" data-testid="mock-mode-callout">
              <span>⚡ Mock Mode Active</span>
            </div>
          )}

          <div className="status-items-list">
            {systemItems.map((item) => (
              <div key={item.name} className="status-item-row">
                <span className="status-item-label">{item.name}</span>
                <span className="status-item-badge">
                  <span className={`status-dot ${item.type}`} />
                  <span>{item.status}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  )
}
