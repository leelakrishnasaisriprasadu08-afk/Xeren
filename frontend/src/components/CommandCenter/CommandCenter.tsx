import React, { useState } from 'react'
import './CommandCenter.css'

interface WorkOrder {
  order_id: string
  platform: string
  client_name: string
  amount_usd: number
  status: string
  workspace_directory: string
  brief?: {
    raw_prompt: string
    project_type: string
  }
}

interface SecurityTiers {
  liberal: { status: string; encryption: string }
  sensitive: { status: string; encryption: string; timeout_minutes: number }
  more_sensitive: { status: string; encryption: string; timeout_minutes: number }
  granted_directories: Array<{ path: string; granted_at: string; allow_write: number }>
}

interface ResearchAngle {
  angle_type: string
  query: string
  rationale: string
  target_domain_tier: string
}

export interface CommandCenterProps {
  activeTab?: 'freelance' | 'security' | 'research' | 'channels'
  onTabChange?: (tab: 'freelance' | 'security' | 'research' | 'channels') => void
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  activeTab: controlledTab,
  onTabChange,
}) => {
  const [internalTab, setInternalTab] = useState<'freelance' | 'security' | 'research' | 'channels'>('freelance')
  const activeTab = controlledTab ?? internalTab

  const handleTabClick = (tab: 'freelance' | 'security' | 'research' | 'channels') => {
    setInternalTab(tab)
    onTabChange?.(tab)
  }

  // Freelance State
  const [orders, setOrders] = useState<WorkOrder[]>([
    {
      order_id: 'FIVERR-9821',
      platform: 'fiverr',
      client_name: 'Sarah Miller',
      amount_usd: 250.0,
      status: 'acknowledged',
      workspace_directory: '~/.xeren/workspaces/fiverr/order_FIVERR-9821',
      brief: {
        raw_prompt: 'Build modern landing page for artisan organic tea brand with interactive brew guide',
        project_type: 'website',
      },
    },
    {
      order_id: 'UPWORK-402',
      platform: 'upwork',
      client_name: 'Apex Corp',
      amount_usd: 1200.0,
      status: 'in_progress',
      workspace_directory: '~/.xeren/workspaces/upwork/order_UPWORK-402',
      brief: {
        raw_prompt: 'Python pipeline to ingest and normalize high-frequency telemetry data',
        project_type: 'coding',
      },
    },
  ])

  // Security Tiers State
  const [securityData, setSecurityData] = useState<SecurityTiers>({
    liberal: { status: 'unlocked', encryption: 'None (Fast Path)' },
    sensitive: { status: 'unlocked', encryption: 'AES-256-CBC', timeout_minutes: 30 },
    more_sensitive: { status: 'locked', encryption: 'AES-256-GCM', timeout_minutes: 10 },
    granted_directories: [
      { path: 'C:/Users/leela/Projects/Xeren', granted_at: '2026-09-07T12:00:00Z', allow_write: 1 },
      { path: 'C:/Users/leela/Documents/Clients', granted_at: '2026-09-07T13:15:00Z', allow_write: 1 },
    ],
  })

  const [pinInput, setPinInput] = useState('')
  const [unlockMessage, setUnlockMessage] = useState('')

  // Research State
  const [researchTopic, setResearchTopic] = useState('Solid-State Batteries: Commercial Readiness & Limitations')
  const [researchAngles, setResearchAngles] = useState<ResearchAngle[]>([
    {
      angle_type: 'factual',
      query: 'solid state battery architecture electrolyte technical overview',
      rationale: 'Establish core chemical mechanics and solid electrolyte conductivity thresholds.',
      target_domain_tier: 'authority',
    },
    {
      angle_type: 'counterfactual',
      query: 'solid state battery degradation dendrite formation failure modes',
      rationale: 'Strawberry AI stress-testing: analyze failure points under fast charging.',
      target_domain_tier: 'trusted_news',
    },
    {
      angle_type: 'statistical',
      query: 'solid state EV energy density Wh/kg cycle life benchmark statistics',
      rationale: 'Empirical real-world benchmark metrics and laboratory test results.',
      target_domain_tier: 'authority',
    },
    {
      angle_type: 'consensus',
      query: 'solid state batteries commercial roadmap IEEE nature review 2026',
      rationale: 'Authoritative academic & institutional consensus.',
      target_domain_tier: 'authority',
    },
  ])

  const handleUnlockMoreSensitive = (e: React.FormEvent) => {
    e.preventDefault()
    if (pinInput.length >= 4) {
      setSecurityData((prev) => ({
        ...prev,
        more_sensitive: { ...prev.more_sensitive, status: 'unlocked' },
      }))
      setUnlockMessage('Tier unlocked silently for this session (10m inactivity window).')
      setPinInput('')
    } else {
      setUnlockMessage('PIN must be at least 4 digits.')
    }
  }

  const handleExecuteOrder = (orderId: string) => {
    setOrders((prev) =>
      prev.map((o) => (o.order_id === orderId ? { ...o, status: 'delivered' } : o))
    )
  }

  const handleAnalyzeTopic = () => {
    if (!researchTopic.trim()) return
    setResearchAngles([
      {
        angle_type: 'factual',
        query: `${researchTopic} overview technical documentation`,
        rationale: 'Establish core definitions and architectural mechanisms.',
        target_domain_tier: 'authority',
      },
      {
        angle_type: 'counterfactual',
        query: `${researchTopic} limitations criticisms risks`,
        rationale: 'Strawberry AI stress-testing: assess edge cases and counter-perspectives.',
        target_domain_tier: 'trusted_news',
      },
      {
        angle_type: 'statistical',
        query: `${researchTopic} empirical benchmark statistics metrics`,
        rationale: 'Retrieve quantified real-world data and benchmark measurements.',
        target_domain_tier: 'authority',
      },
    ])
  }

  return (
    <div className="command-center-container" data-testid="command-center">
      {/* Header Tabs */}
      <div className="command-center-tabs">
        <button
          className={`tab-btn ${activeTab === 'freelance' ? 'active' : ''}`}
          onClick={() => handleTabClick('freelance')}
        >
          <span className="tab-icon">💼</span>
          Freelance Workspaces
          <span className="badge">{orders.length}</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => handleTabClick('security')}
        >
          <span className="tab-icon">🛡️</span>
          3-Tier Security Vault
        </button>
        <button
          className={`tab-btn ${activeTab === 'research' ? 'active' : ''}`}
          onClick={() => handleTabClick('research')}
        >
          <span className="tab-icon">🍓</span>
          Strawberry Research Hub
        </button>
        <button
          className={`tab-btn ${activeTab === 'channels' ? 'active' : ''}`}
          onClick={() => handleTabClick('channels')}
        >
          <span className="tab-icon">💬</span>
          Chat & Voice Gateways
        </button>
      </div>

      {/* Tab 1: Freelance Workspaces */}
      {activeTab === 'freelance' && (
        <div className="tab-pane">
          <div className="pane-header">
            <h3>Autonomous Multi-Platform Workspaces</h3>
            <span className="live-tag">● Personal & Freelance Running In Parallel</span>
          </div>
          <p className="pane-desc">
            Xeren manages isolated client contexts for Fiverr, Upwork, Freelancer, and LinkedIn.
            Orders receive instant automated acknowledgments in &lt;2 minutes, deliverables are built in dedicated folders, and personal work is never interrupted.
          </p>

          <div className="orders-grid">
            {orders.map((order) => (
              <div key={order.order_id} className="order-card">
                <div className="order-card-header">
                  <span className={`platform-badge ${order.platform}`}>{order.platform.toUpperCase()}</span>
                  <span className={`status-badge ${order.status}`}>{order.status.replace('_', ' ').toUpperCase()}</span>
                </div>
                <h4 className="order-title">Order #{order.order_id} • {order.client_name}</h4>
                <p className="order-prompt">"{order.brief?.raw_prompt}"</p>
                <div className="order-meta">
                  <span>💰 ${order.amount_usd}</span>
                  <span>📁 {order.workspace_directory.split('/').pop()}</span>
                </div>
                <div className="order-actions">
                  {order.status !== 'delivered' ? (
                    <button className="execute-btn" onClick={() => handleExecuteOrder(order.order_id)}>
                      ⚡ Build & Deliver Project
                    </button>
                  ) : (
                    <span className="delivered-tag">✓ Packaged & Delivered</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: 3-Tier Security Vault */}
      {activeTab === 'security' && (
        <div className="tab-pane">
          <div className="pane-header">
            <h3>8-Layer Security & 3-Tier Data Vault</h3>
            <span className="live-tag">● Zero External Leaks • PBKDF2 Protected</span>
          </div>
          <p className="pane-desc">
            Every file is sorted into Liberal, Sensitive, or More Sensitive blocks.
            Persistent directory grants ensure you are only asked for permissions ONCE.
          </p>

          <div className="tiers-grid">
            <div className="tier-card liberal">
              <div className="tier-header">
                <h4>🟢 Liberal Block</h4>
                <span className="tier-status">Fast Path</span>
              </div>
              <p>Source code, markdown notes, documentation. Direct local access with no barriers.</p>
              <div className="tier-crypto">Encryption: None (Zero Overhead)</div>
            </div>

            <div className="tier-card sensitive">
              <div className="tier-header">
                <h4>🟡 Sensitive Block</h4>
                <span className={`tier-status ${securityData.sensitive.status}`}>
                  {securityData.sensitive.status.toUpperCase()}
                </span>
              </div>
              <p>Personal photos, videos, contacts, client briefs. Unlocked once per session (30m activity window).</p>
              <div className="tier-crypto">Encryption: AES-256-CBC • Memory Fenced</div>
            </div>

            <div className="tier-card more-sensitive">
              <div className="tier-header">
                <h4>🔴 More Sensitive Block</h4>
                <span className={`tier-status ${securityData.more_sensitive.status}`}>
                  {securityData.more_sensitive.status.toUpperCase()}
                </span>
              </div>
              <p>Aadhaar, passport, bank statements, private keys. Network HARD BLOCKED, prompt zeroing.</p>
              <div className="tier-crypto">Encryption: AES-256-GCM (NIST 600k PBKDF2)</div>

              {securityData.more_sensitive.status === 'locked' && (
                <form onSubmit={handleUnlockMoreSensitive} className="unlock-form">
                  <input
                    type="password"
                    placeholder="Enter 4-digit PIN"
                    value={pinInput}
                    onChange={(e) => setPinInput(e.target.value)}
                    maxLength={6}
                    className="pin-input"
                  />
                  <button type="submit" className="unlock-btn">Unlock Tier</button>
                </form>
              )}
              {unlockMessage && <p className="unlock-msg">{unlockMessage}</p>}
            </div>
          </div>

          <div className="grants-section">
            <h4>Persistent Directory Grants (Approved Once)</h4>
            <div className="grants-list">
              {securityData.granted_directories.map((g) => (
                <div key={g.path} className="grant-row">
                  <span className="grant-path">{g.path}</span>
                  <span className="grant-perm">Read & Write (Permanent)</span>
                  <span className="grant-badge">✓ Authorized</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Strawberry Research Hub */}
      {activeTab === 'research' && (
        <div className="tab-pane">
          <div className="pane-header">
            <h3>Strawberry AI Research & Credibility Hub</h3>
            <span className="live-tag">● Multi-Angle Search • Fact Verification</span>
          </div>
          <p className="pane-desc">
            Xeren rejects random web queries. The Strawberry strategy decomposes topics into factual, counter-factual, and statistical angles, enforcing domain credibility scoring.
          </p>

          <div className="research-search-bar">
            <input
              type="text"
              value={researchTopic}
              onChange={(e) => setResearchTopic(e.target.value)}
              className="research-input"
            />
            <button className="plan-btn" onClick={handleAnalyzeTopic}>🍓 Strawberry Analyze</button>
          </div>

          <div className="angles-grid">
            {researchAngles.map((angle) => (
              <div key={angle.angle_type} className="angle-card">
                <div className="angle-header">
                  <span className={`angle-type-tag ${angle.angle_type}`}>{angle.angle_type.toUpperCase()}</span>
                  <span className="domain-tier-tag">🎯 {angle.target_domain_tier}</span>
                </div>
                <div className="angle-query">"{angle.query}"</div>
                <p className="angle-rationale">{angle.rationale}</p>
              </div>
            ))}
          </div>

          <div className="cross-verification-box">
            <h4>Cross-Verification Matrix</h4>
            <div className="verification-item verified">
              <span className="v-status">✓ VERIFIED</span>
              <span className="v-claim">Solid-state pouch cells demonstrate 80% charge retention after 1,000 cycles at 25°C.</span>
              <span className="v-sources">Corroborated by: Nature Materials (0.95), NIST Lab (0.98)</span>
            </div>
            <div className="verification-item contested">
              <span className="v-status">⚠ CONTESTED</span>
              <span className="v-claim">Full commercial production readiness across mainstream auto manufacturers by Q4 2026.</span>
              <span className="v-sources">Split: Reuters (0.88) claims yes, Scientific American (0.90) reports yield bottleneck</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Chat & Voice Gateways */}
      {activeTab === 'channels' && (
        <div className="tab-pane">
          <div className="pane-header">
            <h3>Omni-Channel Connectors & Voice Engine</h3>
            <span className="live-tag">● 100% Local Inference • Zero Cloud STT/TTS</span>
          </div>

          <div className="gateways-grid">
            <div className="gateway-card">
              <div className="gateway-header">
                <h4>🎙️ Local Speech Engine</h4>
                <span className="status-badge connected">ACTIVE</span>
              </div>
              <p>Whisper local STT + Piper Natural Voice TTS. Audio buffers are zero-filled immediately via SecureMemoryFence.</p>
              <div className="gateway-meta">Latency: &lt;180ms • Local GPU/CPU</div>
            </div>

            <div className="gateway-card">
              <div className="gateway-header">
                <h4>✈️ Telegram Bot Gateway</h4>
                <span className="status-badge connected">CONNECTED</span>
              </div>
              <p>Forward freelance status, trigger research summaries, or chat via encrypted Telegram tunnel.</p>
              <div className="gateway-meta">Auth: Token Vaulted • Challenge Protected</div>
            </div>

            <div className="gateway-card">
              <div className="gateway-header">
                <h4>🎮 Discord Gateway</h4>
                <span className="status-badge connected">CONNECTED</span>
              </div>
              <p>Autonomous notifications when freelance deliverables are ready or critical orders arrive.</p>
              <div className="gateway-meta">Webhook: Encrypted • Channel Broadcast</div>
            </div>

            <div className="gateway-card">
              <div className="gateway-header">
                <h4>📱 WhatsApp Bridge</h4>
                <span className="status-badge connected">READY</span>
              </div>
              <p>Local webhook bridge for high-priority client message notifications.</p>
              <div className="gateway-meta">Security: Local Sandbox</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
