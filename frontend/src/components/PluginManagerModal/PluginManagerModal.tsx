import React, { useState } from 'react'
import './PluginManagerModal.css'

export interface PluginItem {
  id: string
  name: string
  version: string
  category: string
  description: string
  enabled: boolean
  toolsCount: number
  securityLevel: 'Liberal' | 'Sensitive' | 'More Sensitive'
  author: string
}

interface PluginManagerModalProps {
  isOpen: boolean
  onClose: () => void
}

export const PluginManagerModal: React.FC<PluginManagerModalProps> = ({ isOpen, onClose }) => {
  const [plugins, setPlugins] = useState<PluginItem[]>([
    {
      id: 'strawberry_research',
      name: 'Strawberry AI Research',
      version: '2.1.0',
      category: 'Intelligence',
      description: '4-angle query decomposition, multi-source cross-verification matrix, and domain authority ranking.',
      enabled: true,
      toolsCount: 6,
      securityLevel: 'Liberal',
      author: 'Xeren Core',
    },
    {
      id: 'multi_platform_freelance',
      name: 'Freelance Automation',
      version: '1.4.0',
      category: 'Automation',
      description: 'Concurrent isolated workspaces for Fiverr, Upwork, Freelancer, and LinkedIn with <2min auto-response.',
      enabled: true,
      toolsCount: 8,
      securityLevel: 'Sensitive',
      author: 'Xeren Core',
    },
    {
      id: 'local_code_engine',
      name: 'Local Code Engine',
      version: '3.0.0',
      category: 'Development',
      description: 'Full-stack web and script generator using local fine-tuned LLM models without external API keys.',
      enabled: true,
      toolsCount: 12,
      securityLevel: 'Liberal',
      author: 'Xeren Core',
    },
    {
      id: 'security_gate',
      name: '8-Layer Security Gate',
      version: '1.0.0',
      category: 'Security',
      description: 'AES-256-GCM hardware crypto, ctypes buffer zeroing, PBKDF2 PIN store, and strict network isolation guard.',
      enabled: true,
      toolsCount: 9,
      securityLevel: 'More Sensitive',
      author: 'Xeren Core',
    },
    {
      id: 'qdrant_rag',
      name: 'Qdrant Vector RAG',
      version: '1.19.0',
      category: 'Knowledge',
      description: 'High-speed local dense semantic vector search with Cosine distance and automated dimensionality reconciler.',
      enabled: true,
      toolsCount: 5,
      securityLevel: 'Sensitive',
      author: 'Qdrant / Xeren',
    },
    {
      id: 'voice_speech',
      name: 'Offline Whisper STT & TTS',
      version: '1.2.0',
      category: 'Audio',
      description: 'Local OpenAI Whisper offline speech-to-text with audio memory fencing and zero telemetry.',
      enabled: true,
      toolsCount: 4,
      securityLevel: 'Sensitive',
      author: 'Xeren Core',
    },
  ])

  const [activeFilter, setActiveFilter] = useState<'all' | 'enabled' | 'security'>('all')

  if (!isOpen) return null

  const handleToggle = (id: string) => {
    setPlugins((prev) =>
      prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p))
    )
  }

  const filteredPlugins = plugins.filter((p) => {
    if (activeFilter === 'enabled') return p.enabled
    if (activeFilter === 'security') return p.securityLevel === 'More Sensitive'
    return true
  })

  return (
    <div
      className="plugin-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Plugin Registry Manager"
      data-testid="plugin-manager-modal"
    >
      <div
        className="plugin-modal-card"
        onClick={(e) => e.stopPropagation()}
        data-testid="plugin-modal-card"
      >
        <div className="plugin-modal-header">
          <div>
            <div className="plugin-modal-subtitle">EXTENSIBLE ARCHITECTURE</div>
            <h2 className="plugin-modal-title">Autonomous Plugin Registry</h2>
          </div>
          <button
            type="button"
            className="plugin-close-btn"
            onClick={onClose}
            aria-label="Close plugin manager"
            data-testid="close-plugin-modal-btn"
          >
            ✕
          </button>
        </div>

        <div className="plugin-modal-filters">
          <button
            type="button"
            className={`filter-btn ${activeFilter === 'all' ? 'active' : ''}`}
            onClick={() => setActiveFilter('all')}
          >
            All Plugins ({plugins.length})
          </button>
          <button
            type="button"
            className={`filter-btn ${activeFilter === 'enabled' ? 'active' : ''}`}
            onClick={() => setActiveFilter('enabled')}
          >
            Active Only ({plugins.filter((p) => p.enabled).length})
          </button>
          <button
            type="button"
            className={`filter-btn ${activeFilter === 'security' ? 'active' : ''}`}
            onClick={() => setActiveFilter('security')}
          >
            High Security ({plugins.filter((p) => p.securityLevel === 'More Sensitive').length})
          </button>
        </div>

        <div className="plugin-list" role="list">
          {filteredPlugins.map((plugin) => (
            <div
              key={plugin.id}
              className={`plugin-card ${plugin.enabled ? 'is-enabled' : 'is-disabled'}`}
              data-testid={`plugin-card-${plugin.id}`}
            >
              <div className="plugin-card-header">
                <div className="plugin-meta-left">
                  <span className="plugin-badge category">{plugin.category}</span>
                  <span className={`plugin-badge tier ${plugin.securityLevel.toLowerCase().replace(' ', '-')}`}>
                    {plugin.securityLevel}
                  </span>
                  <span className="plugin-version">v{plugin.version}</span>
                </div>
                <button
                  type="button"
                  className={`plugin-toggle-btn ${plugin.enabled ? 'active' : ''}`}
                  onClick={() => handleToggle(plugin.id)}
                  aria-pressed={plugin.enabled}
                  data-testid={`toggle-plugin-${plugin.id}`}
                >
                  <span className="toggle-thumb" />
                  <span className="toggle-text">{plugin.enabled ? 'Active' : 'Disabled'}</span>
                </button>
              </div>

              <h4 className="plugin-name">{plugin.name}</h4>
              <p className="plugin-desc">{plugin.description}</p>

              <div className="plugin-footer">
                <span className="plugin-stat">{plugin.toolsCount} Tools Registered</span>
                <span className="plugin-stat author">By {plugin.author}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
