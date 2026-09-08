import React, { useState } from 'react'
import type {
  UserConnectedAccount,
  AccountLoginPayload,
  AddLocalAppPayload,
  AddCustomAppPayload,
  AccountPlanTier,
} from '../../types/account'
import { AppLogo } from './AppLogos'

interface UserAccountsTabProps {
  accounts: UserConnectedAccount[]
  onLogin: (payload: AccountLoginPayload) => Promise<void>
  onLogout: (appId: string) => Promise<void>
  onAddLocalApp?: (payload: AddLocalAppPayload) => Promise<void>
  onAddCustomApp?: (payload: AddCustomAppPayload) => Promise<void>
}

export const UserAccountsTab: React.FC<UserAccountsTabProps> = ({
  accounts,
  onLogin,
  onLogout,
  onAddLocalApp,
  onAddCustomApp,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<
    'all' | 'ai' | 'design' | 'developer' | 'productivity' | 'media' | 'local'
  >('all')
  const [selectedAppForLogin, setSelectedAppForLogin] = useState<UserConnectedAccount | null>(null)

  // Login / Link Form State
  const [emailInput, setEmailInput] = useState('')
  const [nameInput, setNameInput] = useState('')
  const [tokenInput, setTokenInput] = useState('')
  const [endpointInput, setEndpointInput] = useState('')
  const [localPathInput, setLocalPathInput] = useState('')
  const [tierInput, setTierInput] = useState<AccountPlanTier>('pro')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null)

  // Custom App Registration Modal State (URL, API Key, User Details, Local Path)
  const [isAddCustomModalOpen, setIsAddCustomModalOpen] = useState(false)
  const [newAppName, setNewAppName] = useState('')
  const [newAppCategory, setNewAppCategory] = useState('ai')
  const [newConnectionType, setNewConnectionType] = useState<'cloud_api' | 'custom_url' | 'local_device'>('cloud_api')
  const [newAppEndpointUrl, setNewAppEndpointUrl] = useState('')
  const [newAppApiKey, setNewAppApiKey] = useState('')
  const [newAppEmail, setNewAppEmail] = useState('')
  const [newAppUserName, setNewAppUserName] = useState('')
  const [newAppPlanTier, setNewAppPlanTier] = useState<AccountPlanTier>('pro')
  const [newAppPath, setNewAppPath] = useState('')
  const [newAppDesc, setNewAppDesc] = useState('')
  const [isAddingCustom, setIsAddingCustom] = useState(false)

  const handleOpenLogin = (acct: UserConnectedAccount) => {
    setSelectedAppForLogin(acct)
    setEmailInput(acct.user_email || (acct.requires_api_key === false ? 'device@xeren.local' : ''))
    setNameInput(acct.user_name || (acct.requires_api_key === false ? 'Device User' : ''))
    setTokenInput('')
    setEndpointInput(acct.endpoint_url || '')
    setLocalPathInput(acct.local_path || '')
    setTierInput(acct.plan_tier || 'pro')
    setFeedbackMsg(null)
  }

  const handleSubmitLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAppForLogin) return

    const isLocal = selectedAppForLogin.requires_api_key === false || selectedAppForLogin.connection_type === 'local_device'

    // Cloud apps require email & key, local apps do not require an API key
    if (!isLocal && (!emailInput.trim() || !tokenInput.trim())) return

    setIsSubmitting(true)
    setFeedbackMsg(null)
    try {
      await onLogin({
        app_id: selectedAppForLogin.app_id,
        user_email: emailInput.trim() || 'device@xeren.local',
        user_name: nameInput.trim() || (isLocal ? 'Device User' : emailInput.split('@')[0]),
        token_or_key: isLocal ? '' : tokenInput.trim(),
        plan_tier: tierInput,
        local_path: isLocal ? (localPathInput.trim() || selectedAppForLogin.local_path || 'linked') : undefined,
        endpoint_url: endpointInput.trim() || selectedAppForLogin.endpoint_url || undefined,
        connection_type: isLocal ? 'local_device' : 'cloud_api',
      })
      setFeedbackMsg(
        isLocal
          ? `Linked ${selectedAppForLogin.app_name} on device (No API key needed)!`
          : `Successfully authenticated as ${emailInput}!`
      )
      setTimeout(() => {
        setSelectedAppForLogin(null)
        setFeedbackMsg(null)
      }, 900)
    } catch {
      setFeedbackMsg('Failed to authenticate credentials.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCreateCustomApp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newAppName.trim()) return

    setIsAddingCustom(true)
    try {
      const payload: AddCustomAppPayload = {
        app_name: newAppName.trim(),
        category: newAppCategory,
        connection_type: newConnectionType,
        endpoint_url: newAppEndpointUrl.trim() || undefined,
        api_key_or_token: newAppApiKey.trim() || undefined,
        user_email: newAppEmail.trim() || undefined,
        user_name: newAppUserName.trim() || undefined,
        plan_tier: newAppPlanTier,
        local_path: newAppPath.trim() || undefined,
        description: newAppDesc.trim() || undefined,
        capabilities: ['custom-integration', 'cross-app-workflow'],
      }

      if (onAddCustomApp) {
        await onAddCustomApp(payload)
      } else if (onAddLocalApp) {
        await onAddLocalApp({
          app_name: newAppName.trim(),
          category: newAppCategory,
          local_path: newAppPath.trim() || undefined,
          description: newAppDesc.trim() || undefined,
          capabilities: ['custom-integration'],
          user_name: newAppUserName.trim() || undefined,
        })
      }

      setIsAddCustomModalOpen(false)
      setNewAppName('')
      setNewAppEndpointUrl('')
      setNewAppApiKey('')
      setNewAppEmail('')
      setNewAppUserName('')
      setNewAppPath('')
      setNewAppDesc('')
    } finally {
      setIsAddingCustom(false)
    }
  }

  const getTokenLabel = (appId: string) => {
    switch (appId) {
      case 'gemini':
        return 'Google Gemini API Key'
      case 'canva':
        return 'Canva Connect API Key / Session Secret'
      case 'huggingface':
        return 'Hugging Face User Access Token (read/write)'
      case 'openai':
        return 'OpenAI API Secret Key (sk-...)'
      case 'claude':
        return 'Anthropic Claude API Key (sk-ant-...)'
      case 'perplexity':
        return 'Perplexity API Key (pplx-...)'
      case 'midjourney':
        return 'Midjourney API Key / User Token'
      case 'github':
        return 'GitHub Personal Access Token (ghp-...)'
      case 'supabase':
        return 'Supabase Service Role / Anon API Key'
      case 'notion':
        return 'Notion Integration Internal Secret (secret_...)'
      case 'gdrive':
        return 'Google Workspace / Drive OAuth Token'
      case 'slack':
        return 'Slack Bot or User OAuth Token (xoxb/xoxp)'
      case 'discord':
        return 'Discord Bot Token or User OAuth Token'
      case 'spotify':
        return 'Spotify App Client Secret'
      case 'linear':
        return 'Linear Personal API Key (lin_api_...)'
      case 'figma':
        return 'Figma Personal Access Token (figd_...)'
      default:
        return 'Personal API Key / Access Token'
    }
  }

  // Filter accounts according to category
  const filteredAccounts = accounts.filter((acct) => {
    if (selectedCategory === 'all') return true
    if (selectedCategory === 'local') {
      return acct.requires_api_key === false || acct.connection_type === 'local_device' || acct.category === 'local'
    }
    return acct.category === selectedCategory
  })

  const localCount = accounts.filter(
    (a) => a.requires_api_key === false || a.connection_type === 'local_device'
  ).length

  return (
    <div className="user-accounts-container" data-testid="user-accounts-tab-content">
      {/* Banner Header */}
      <div className="accounts-header-banner">
        <div>
          <h4>Connected Apps, Logins & Custom Services</h4>
          <p>
            Connect cloud services, customize <strong>API URLs & secret keys</strong>, manage <strong>user details</strong>,
            or link native computer applications (Blender, VS Code, OBS) with <strong>no API keys needed</strong>.
          </p>
        </div>
        <div className="banner-actions-wrap">
          <button
            type="button"
            className="add-device-app-btn"
            onClick={() => setIsAddCustomModalOpen(true)}
            data-testid="add-local-app-btn"
            title="Add any custom web service or device app with URL, API key, and user details"
          >
            + Add Application (URL / Key / Device)
          </button>
          <div className="vault-security-pill">
            <span>🛡️ AES-256-GCM Hardware Encrypted</span>
          </div>
        </div>
      </div>

      {/* Category Filter Chips */}
      <div className="accounts-filter-bar">
        <button
          type="button"
          className={`filter-chip ${selectedCategory === 'all' ? 'active' : ''}`}
          onClick={() => setSelectedCategory('all')}
        >
          All Platforms ({accounts.length})
        </button>
        <button
          type="button"
          className={`filter-chip ${selectedCategory === 'local' ? 'active' : ''}`}
          onClick={() => setSelectedCategory('local')}
          data-testid="filter-local-apps"
        >
          🖥️ Local Device Apps ({localCount})
        </button>
        <button
          type="button"
          className={`filter-chip ${selectedCategory === 'ai' ? 'active' : ''}`}
          onClick={() => setSelectedCategory('ai')}
        >
          AI & LLMs
        </button>
        <button
          type="button"
          className={`filter-chip ${selectedCategory === 'design' ? 'active' : ''}`}
          onClick={() => setSelectedCategory('design')}
        >
          Design & 3D
        </button>
        <button
          type="button"
          className={`filter-chip ${selectedCategory === 'developer' ? 'active' : ''}`}
          onClick={() => setSelectedCategory('developer')}
        >
          Dev Tools
        </button>
        <button
          type="button"
          className={`filter-chip ${selectedCategory === 'productivity' ? 'active' : ''}`}
          onClick={() => setSelectedCategory('productivity')}
        >
          Productivity
        </button>
        <button
          type="button"
          className={`filter-chip ${selectedCategory === 'media' ? 'active' : ''}`}
          onClick={() => setSelectedCategory('media')}
        >
          Media & Audio
        </button>
      </div>

      {/* Account Cards Grid */}
      <div className="accounts-cards-grid">
        {filteredAccounts.map((acct) => {
          const isAuthed = acct.auth_status === 'authenticated'
          const isLocal = acct.requires_api_key === false || acct.connection_type === 'local_device'

          return (
            <div
              key={acct.app_id}
              className={`account-card ${isAuthed ? 'authenticated' : 'disconnected'} ${isLocal ? 'device-app' : ''}`}
              data-testid={`account-card-${acct.app_id}`}
            >
              <div className="account-card-header">
                <div className="account-brand">
                  <span className="account-icon-wrap" aria-hidden="true">
                    <AppLogo appId={acct.app_id} size={30} />
                  </span>
                  <div>
                    <h5>{acct.app_name}</h5>
                    <div className="badge-row">
                      <span className="account-category">{acct.category.toUpperCase()}</span>
                      {isLocal ? (
                        <span className="local-device-tag" title="No API key required. Runs locally.">
                          🖥️ LOCAL (NO KEY)
                        </span>
                      ) : acct.endpoint_url ? (
                        <span className="custom-url-tag" title={acct.endpoint_url}>
                          🌐 CUSTOM API
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
                <span className={`account-status-badge ${acct.auth_status}`}>
                  {isAuthed ? (isLocal ? '✓ Linked' : '✓ Logged In') : 'Not Connected'}
                </span>
              </div>

              <p className="account-desc">{acct.description}</p>

              {/* Endpoint URL Display if present */}
              {acct.endpoint_url && (
                <div className="account-endpoint-row" title={`Service URL: ${acct.endpoint_url}`}>
                  <span className="endpoint-icon">🔗</span>
                  <code className="endpoint-url-text">{acct.endpoint_url}</code>
                </div>
              )}

              {isAuthed ? (
                <div className="authenticated-info-box">
                  <div className="user-details-row">
                    <span className="user-avatar-pip">{isLocal ? '🖥️' : '👤'}</span>
                    <div>
                      <strong className="user-email-text">
                        {isLocal
                          ? acct.local_path
                            ? `Local: ${acct.local_path}`
                            : 'Installed on Device'
                          : acct.user_email}
                      </strong>
                      <div className="user-meta-sub">
                        <span className="plan-tier-badge">
                          {isLocal ? 'LOCAL DEVICE' : acct.plan_tier.toUpperCase()}
                        </span>
                        <span className="masked-token-code">
                          <code>{acct.masked_token || (isLocal ? 'local:device' : '••••••••')}</code>
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="capabilities-row">
                    {acct.capabilities.map((cap) => (
                      <span key={cap} className="cap-tag">{cap}</span>
                    ))}
                  </div>

                  <div className="account-actions-row">
                    <button
                      type="button"
                      className="switch-account-btn"
                      onClick={() => handleOpenLogin(acct)}
                      data-testid={`switch-account-${acct.app_id}`}
                    >
                      {isLocal ? 'Configure' : 'Configure / Switch'}
                    </button>
                    <button
                      type="button"
                      className="logout-account-btn"
                      onClick={() => onLogout(acct.app_id)}
                      data-testid={`logout-account-${acct.app_id}`}
                    >
                      {isLocal ? 'Unlink' : 'Log Out'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="unauthenticated-info-box">
                  <div className="capabilities-row">
                    {acct.capabilities.map((cap) => (
                      <span key={cap} className="cap-tag">{cap}</span>
                    ))}
                  </div>
                  <button
                    type="button"
                    className={`login-account-btn ${isLocal ? 'link-device-btn' : ''}`}
                    onClick={() => handleOpenLogin(acct)}
                    data-testid={`login-btn-${acct.app_id}`}
                  >
                    {isLocal ? '⚡ Link to Device (No API Key)' : '+ Log In as User Account'}
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Login / Link Dialog */}
      {selectedAppForLogin && (
        <div className="login-modal-overlay" onClick={() => setSelectedAppForLogin(null)}>
          <div className="login-modal-card" onClick={(e) => e.stopPropagation()} data-testid="login-modal-card">
            <div className="login-modal-top">
              <div className="login-app-identity">
                <span className="modal-icon-wrap">
                  <AppLogo appId={selectedAppForLogin.app_id} size={38} />
                </span>
                <div>
                  <h4>
                    {selectedAppForLogin.requires_api_key === false
                      ? `Link ${selectedAppForLogin.app_name} on Device`
                      : `Log In to ${selectedAppForLogin.app_name}`}
                  </h4>
                  <p>
                    {selectedAppForLogin.requires_api_key === false
                      ? 'Operates directly on your computer without an API key.'
                      : 'Authenticate with your user credentials to run tools under your account.'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="close-login-modal-btn"
                onClick={() => setSelectedAppForLogin(null)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitLogin} className="login-form">
              {selectedAppForLogin.requires_api_key === false ? (
                // Local Device App Fields (No API Key Required)
                <>
                  <div className="local-app-highlight-box">
                    <span className="highlight-icon">💡</span>
                    <div>
                      <strong>No API Key Required</strong>
                      <p>
                        This application runs locally on your device. Xeren triggers automation via local CLI,
                        IPC, or scripting interfaces.
                      </p>
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="local-path-input">Executable Path / Launch Command</label>
                    <input
                      id="local-path-input"
                      type="text"
                      placeholder={selectedAppForLogin.local_path || 'e.g., blender, code, obs64.exe'}
                      value={localPathInput}
                      onChange={(e) => setLocalPathInput(e.target.value)}
                      data-testid="login-input-local-path"
                    />
                    <span className="input-hint">
                      Defaults to system path if installed (e.g. <code>{selectedAppForLogin.local_path || 'system'}</code>).
                    </span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="user-name-input">User / Profile Label</label>
                    <input
                      id="user-name-input"
                      type="text"
                      placeholder="e.g., Primary Workstation"
                      value={nameInput}
                      onChange={(e) => setNameInput(e.target.value)}
                    />
                  </div>
                </>
              ) : (
                // Cloud / Custom Web API Fields (URL, API Key, User Details)
                <>
                  {selectedAppForLogin.endpoint_url && (
                    <div className="form-group">
                      <label htmlFor="user-endpoint-input">Endpoint / Base Service URL</label>
                      <input
                        id="user-endpoint-input"
                        type="url"
                        placeholder="https://api.domain.com/v1"
                        value={endpointInput}
                        onChange={(e) => setEndpointInput(e.target.value)}
                        data-testid="login-input-endpoint"
                      />
                    </div>
                  )}

                  <div className="form-group">
                    <label htmlFor="user-email-input">User Account Email / Username</label>
                    <input
                      id="user-email-input"
                      type="email"
                      placeholder="e.g., yourname@domain.com"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      required
                      data-testid="login-input-email"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="user-name-input">Display Name (Optional)</label>
                    <input
                      id="user-name-input"
                      type="text"
                      placeholder="e.g., Leela"
                      value={nameInput}
                      onChange={(e) => setNameInput(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="user-token-input">
                      {getTokenLabel(selectedAppForLogin.app_id)}
                    </label>
                    <input
                      id="user-token-input"
                      type="password"
                      placeholder="••••••••••••••••••••••••"
                      value={tokenInput}
                      onChange={(e) => setTokenInput(e.target.value)}
                      required
                      data-testid="login-input-token"
                    />
                    <span className="input-hint">
                      Stored locally in UserVault encrypted with AES-256-GCM.
                    </span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="user-tier-select">Account Plan Tier</label>
                    <select
                      id="user-tier-select"
                      value={tierInput}
                      onChange={(e) => setTierInput(e.target.value as any)}
                    >
                      <option value="free">Free / Personal</option>
                      <option value="pro">Pro / Plus / Team</option>
                      <option value="enterprise">Enterprise / Unlimited</option>
                    </select>
                  </div>
                </>
              )}

              {feedbackMsg && (
                <div className="login-feedback-alert">
                  {feedbackMsg}
                </div>
              )}

              <div className="login-modal-actions">
                <button
                  type="button"
                  className="cancel-btn"
                  onClick={() => setSelectedAppForLogin(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="submit-login-btn"
                  disabled={isSubmitting}
                  data-testid="submit-account-login-btn"
                >
                  {isSubmitting
                    ? 'Connecting...'
                    : selectedAppForLogin.requires_api_key === false
                    ? '⚡ Link Application to Device'
                    : 'Authenticate & Save Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Register Universal Custom Application (URL, API Key, User Details, Device) */}
      {isAddCustomModalOpen && (
        <div className="login-modal-overlay" onClick={() => setIsAddCustomModalOpen(false)}>
          <div
            className="login-modal-card custom-device-modal"
            onClick={(e) => e.stopPropagation()}
            data-testid="add-local-device-modal"
          >
            <div className="login-modal-top">
              <div className="login-app-identity">
                <span className="modal-icon-wrap">
                  <AppLogo appId={newConnectionType === 'local_device' ? 'device' : 'custom'} size={38} />
                </span>
                <div>
                  <h4>Add Application or Custom Service</h4>
                  <p>Configure endpoint URL, API key, user details, or link a local program.</p>
                </div>
              </div>
              <button
                type="button"
                className="close-login-modal-btn"
                onClick={() => setIsAddCustomModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateCustomApp} className="login-form">
              {/* Connection Mode Selector */}
              <div className="connection-mode-selector">
                <label className="section-label">Connection Mode</label>
                <div className="mode-toggle-group">
                  <button
                    type="button"
                    className={`mode-btn ${newConnectionType === 'cloud_api' ? 'active' : ''}`}
                    onClick={() => setNewConnectionType('cloud_api')}
                  >
                    🌐 Web Service / API
                  </button>
                  <button
                    type="button"
                    className={`mode-btn ${newConnectionType === 'custom_url' ? 'active' : ''}`}
                    onClick={() => setNewConnectionType('custom_url')}
                  >
                    🔗 Custom URL / Webhook
                  </button>
                  <button
                    type="button"
                    className={`mode-btn ${newConnectionType === 'local_device' ? 'active' : ''}`}
                    onClick={() => setNewConnectionType('local_device')}
                  >
                    🖥️ Local Device App
                  </button>
                </div>
              </div>

              {/* 1. App Identity Section */}
              <div className="form-section-box">
                <span className="section-legend">1. Application Identity</span>
                <div className="form-group">
                  <label htmlFor="custom-app-name">Application Name *</label>
                  <input
                    id="custom-app-name"
                    type="text"
                    placeholder="e.g., Ollama Local AI, Godot Engine, Custom LLM Gateway"
                    value={newAppName}
                    onChange={(e) => setNewAppName(e.target.value)}
                    required
                    data-testid="custom-app-name-input"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="custom-app-category">Category</label>
                  <select
                    id="custom-app-category"
                    value={newAppCategory}
                    onChange={(e) => setNewAppCategory(e.target.value)}
                    data-testid="custom-app-category-select"
                  >
                    <option value="ai">AI & Machine Learning</option>
                    <option value="design">Design, 3D & Creative</option>
                    <option value="developer">Developer, API & Cloud</option>
                    <option value="productivity">Productivity & Docs</option>
                    <option value="media">Media & Audio Streaming</option>
                    <option value="tools">System Tools & Utilities</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="custom-app-desc">Description (Optional)</label>
                  <input
                    id="custom-app-desc"
                    type="text"
                    placeholder="e.g., Self-hosted Llama-3 models via local Ollama server"
                    value={newAppDesc}
                    onChange={(e) => setNewAppDesc(e.target.value)}
                  />
                </div>
              </div>

              {/* 2. URL & Endpoint Part (when not local_device) */}
              {newConnectionType !== 'local_device' ? (
                <div className="form-section-box">
                  <span className="section-legend">2. URL Endpoint Part</span>
                  <div className="form-group">
                    <label htmlFor="custom-app-endpoint">Base URL / Endpoint / Webhook URL</label>
                    <input
                      id="custom-app-endpoint"
                      type="url"
                      placeholder="e.g., https://api.openai.com/v1 or http://localhost:11434"
                      value={newAppEndpointUrl}
                      onChange={(e) => setNewAppEndpointUrl(e.target.value)}
                      data-testid="custom-app-url-input"
                    />
                    <span className="input-hint">
                      The network address or REST/HTTP gateway for API dispatch.
                    </span>
                  </div>
                </div>
              ) : (
                <div className="form-section-box">
                  <span className="section-legend">2. Local Computer Path (No API Key Required)</span>
                  <div className="form-group">
                    <label htmlFor="custom-app-path">Executable Path or Terminal Command</label>
                    <input
                      id="custom-app-path"
                      type="text"
                      placeholder="e.g., godot.exe, C:\Program Files\Audacity\audacity.exe, or code"
                      value={newAppPath}
                      onChange={(e) => setNewAppPath(e.target.value)}
                      data-testid="custom-app-path-input"
                    />
                    <span className="input-hint">
                      System command in PATH or absolute executable file location on your machine.
                    </span>
                  </div>
                </div>
              )}

              {/* 3. API Key Part (when not local_device) */}
              {newConnectionType !== 'local_device' && (
                <div className="form-section-box">
                  <span className="section-legend">3. API Key & Security Part</span>
                  <div className="form-group">
                    <label htmlFor="custom-app-key">API Key / Access Token / Bearer Secret</label>
                    <input
                      id="custom-app-key"
                      type="password"
                      placeholder="••••••••••••••••••••••••"
                      value={newAppApiKey}
                      onChange={(e) => setNewAppApiKey(e.target.value)}
                      data-testid="custom-app-key-input"
                    />
                    <span className="input-hint">
                      Encrypted in UserVault with hardware-grade AES-256-GCM. Optional for public/local endpoints.
                    </span>
                  </div>
                </div>
              )}

              {/* 4. User Account Details Part */}
              <div className="form-section-box">
                <span className="section-legend">
                  {newConnectionType === 'local_device' ? '3. User Profile Details' : '4. User Account Details Part'}
                </span>
                <div className="form-group">
                  <label htmlFor="custom-app-email">User Email / Account Username</label>
                  <input
                    id="custom-app-email"
                    type="text"
                    placeholder="e.g., yourname@domain.com or developer"
                    value={newAppEmail}
                    onChange={(e) => setNewAppEmail(e.target.value)}
                    data-testid="custom-app-email-input"
                  />
                </div>

                <div className="form-row-2col">
                  <div className="form-group">
                    <label htmlFor="custom-app-username">Display Name / Org</label>
                    <input
                      id="custom-app-username"
                      type="text"
                      placeholder="e.g., Leela / Workspace"
                      value={newAppUserName}
                      onChange={(e) => setNewAppUserName(e.target.value)}
                      data-testid="custom-app-username-input"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="custom-app-tier">Plan Tier</label>
                    <select
                      id="custom-app-tier"
                      value={newAppPlanTier}
                      onChange={(e) => setNewAppPlanTier(e.target.value as any)}
                      data-testid="custom-app-tier-select"
                    >
                      <option value="free">Free / Personal</option>
                      <option value="pro">Pro / Team</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="login-modal-actions">
                <button
                  type="button"
                  className="cancel-btn"
                  onClick={() => setIsAddCustomModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="submit-login-btn"
                  disabled={isAddingCustom || !newAppName.trim()}
                  data-testid="submit-add-local-app-btn"
                >
                  {isAddingCustom ? 'Registering...' : '+ Save & Connect Application'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
