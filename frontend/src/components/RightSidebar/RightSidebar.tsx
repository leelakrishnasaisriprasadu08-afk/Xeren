import React, { useState, useEffect, useRef } from 'react'
import type { ConnectionState } from '../../types/realtime'
import './RightSidebar.css'

interface RightSidebarProps {
  isOpen?: boolean
  onToggle?: () => void
  onClose?: () => void
  transportType: string
  connectionState: ConnectionState
  onSelectPrompt: (prompt: string) => void
  onOpenPlugins?: () => void
  onOpenKnowledge?: () => void
  onOpenConnectedApps?: () => void
  onOpenImprovementHub?: () => void
  onOpenWorkspaces?: (tab?: 'freelance' | 'security' | 'research' | 'channels') => void
}

export const RightSidebar: React.FC<RightSidebarProps> = ({
  isOpen: controlledOpen,
  onToggle,
  onClose,
  transportType,
  connectionState,
  onSelectPrompt,
  onOpenPlugins,
  onOpenKnowledge,
  onOpenConnectedApps,
  onOpenImprovementHub,
  onOpenWorkspaces,
}) => {
  const [internalOpen, setInternalOpen] = useState(false)
  const isControlled = typeof controlledOpen === 'boolean'
  const isPanelOpen = isControlled ? controlledOpen : internalOpen

  const isMock = transportType === 'mock'
  const isConnected = connectionState === 'connected'

  const [isDiagnosing, setIsDiagnosing] = useState(false)
  const [diagResult, setDiagResult] = useState<string | null>(null)
  const hubRef = useRef<HTMLDivElement>(null)

  const handleToggle = () => {
    if (onToggle) {
      onToggle()
    } else {
      setInternalOpen((prev) => !prev)
    }
  }

  const handleClose = () => {
    if (onClose) {
      onClose()
    } else {
      setInternalOpen(false)
    }
  }

  // Close on Escape key or outside click
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isPanelOpen) {
        handleClose()
      }
    }
    const handleClickOutside = (e: MouseEvent) => {
      if (
        isPanelOpen &&
        hubRef.current &&
        !hubRef.current.contains(e.target as Node)
      ) {
        handleClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isPanelOpen])

  const handleRunDiagnostics = async () => {
    setIsDiagnosing(true)
    setDiagResult(null)
    const startTime = performance.now()
    try {
      const res = await fetch('http://127.0.0.1:8000/api/health')
      const elapsed = Math.round(performance.now() - startTime)
      if (res.ok) {
        const data = await res.json()
        setDiagResult(`FastAPI live (${elapsed}ms) • Storage: ${data.storage} • Dispatcher: Ready`)
      } else {
        setDiagResult(`API responded with ${res.status} (${elapsed}ms)`)
      }
    } catch {
      const elapsed = Math.round(performance.now() - startTime)
      setDiagResult(`Local Runtime: Offline (${elapsed}ms) - using Client Engine`)
    } finally {
      setIsDiagnosing(false)
    }
  }

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
      action: () => {
        onSelectPrompt('Create a modern, responsive website with interactive components')
        handleClose()
      },
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
      action: () => {
        onSelectPrompt('Research the latest research papers and benchmarks on AI agents')
        handleClose()
      },
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
      action: () => {
        if (onOpenPlugins) {
          onOpenPlugins()
        } else {
          onSelectPrompt('Activate plugins for coding, research, and data workflows')
        }
        handleClose()
      },
    },
    {
      id: 'open-knowledge',
      label: 'Knowledge Vault',
      prompt: 'Explore Qdrant vector embeddings and indexed documents',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
      ),
      action: () => {
        if (onOpenKnowledge) {
          onOpenKnowledge()
        } else {
          onSelectPrompt('Explore Qdrant vector embeddings and indexed documents')
        }
        handleClose()
      },
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
      action: () => {
        if (onOpenWorkspaces) {
          onOpenWorkspaces('freelance')
        } else {
          onSelectPrompt('Summarize the active project status, files, and tasks')
        }
        handleClose()
      },
    },
  ]

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
    <div className="floating-hub-container" ref={hubRef} data-testid="floating-hub-wrapper">
      {/* 1. Floating Action Button in the Bottom-Right Corner */}
      <button
        type="button"
        className={`floating-hub-trigger ${isPanelOpen ? 'active' : ''}`}
        onClick={handleToggle}
        title={isPanelOpen ? 'Close Action Palette' : 'Open Quick Command Hub'}
        aria-label="Toggle Quick Command Hub"
        aria-expanded={isPanelOpen}
        data-testid="floating-hub-trigger"
      >
        <span className="hub-trigger-ambient" />
        <span className={`hub-status-pip ${isConnected ? 'online' : 'simulated'}`} />
        <div className="hub-icon-wrap">
          {isPanelOpen ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          )}
        </div>
        {!isPanelOpen && <span className="hub-trigger-tooltip">Quick Actions</span>}
      </button>

      {/* 2. Expanded Floating Command Palette (Silky pleasant transition) */}
      <aside
        className={`right-sidebar floating-chart-panel ${isPanelOpen ? 'open' : ''}`}
        aria-label="Quick actions and system status"
        data-testid="right-sidebar"
      >
        {/* Header */}
        <div className="hub-panel-header">
          <div className="hub-header-title">
            <span className="hub-category">COMMAND HUB</span>
            <h4>Actions & Telemetry</h4>
          </div>
          <button
            type="button"
            className="hub-close-btn"
            onClick={handleClose}
            aria-label="Close command hub"
            data-testid="close-hub-btn"
          >
            ✕
          </button>
        </div>

        {/* Subsystem Direct Jumpers Grid */}
        <div className="hub-subsystems-row">
          <button
            type="button"
            className="hub-sub-chip"
            onClick={() => {
              onOpenWorkspaces?.('freelance')
              handleClose()
            }}
            title="Freelance Workspaces"
          >
            <span>💼 Freelance</span>
          </button>
          <button
            type="button"
            className="hub-sub-chip"
            onClick={() => {
              onOpenWorkspaces?.('research')
              handleClose()
            }}
            title="Strawberry AI Research"
          >
            <span>🍓 Research</span>
          </button>
          <button
            type="button"
            className="hub-sub-chip"
            onClick={() => {
              onOpenWorkspaces?.('security')
              handleClose()
            }}
            title="3-Tier Security Vault"
          >
            <span>🛡️ Security</span>
          </button>
          <button
            type="button"
            className="hub-sub-chip"
            onClick={() => {
              onOpenPlugins?.()
              handleClose()
            }}
            title="Plugins Registry"
          >
            <span>🧩 Plugins</span>
          </button>
          <button
            type="button"
            className="hub-sub-chip"
            onClick={() => {
              onOpenKnowledge?.()
              handleClose()
            }}
            title="Knowledge Vault"
          >
            <span>📚 Vault</span>
          </button>
          <button
            type="button"
            className="hub-sub-chip"
            onClick={() => {
              onOpenConnectedApps?.()
              handleClose()
            }}
            title="Connected Apps & MCP Hub"
            data-testid="hub-chip-apps"
          >
            <span>🔌 Apps (MCP)</span>
          </button>
          <button
            type="button"
            className="hub-sub-chip"
            onClick={() => {
              onOpenImprovementHub?.()
              handleClose()
            }}
            title="Neural Learning & LLM Self-Improvement Hub"
            data-testid="hub-chip-improvements"
          >
            <span>🧠 Adaptive AI</span>
          </button>
        </div>

        {/* Quick Actions List */}
        <div className="right-section">
          <div className="right-section-title">
            <span>Quick Prompts</span>
          </div>
          <div className="quick-actions-list">
            {quickActions.map((action) => (
              <button
                key={action.id}
                type="button"
                className="quick-action-btn"
                onClick={action.action}
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

        {/* System Telemetry & Diagnostics */}
        <div className="right-section">
          <div className="right-section-title">
            <span>System Telemetry</span>
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

            {/* Real Diagnostics Trigger Button */}
            <div className="diagnostics-action-row">
              <button
                type="button"
                className="diagnostics-btn"
                onClick={handleRunDiagnostics}
                disabled={isDiagnosing}
                data-testid="run-diagnostics-btn"
              >
                {isDiagnosing ? 'Testing Latency...' : '⚡ Run Diagnostics'}
              </button>
              {diagResult && (
                <div className="diag-feedback" data-testid="diagnostics-result">
                  {diagResult}
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}
