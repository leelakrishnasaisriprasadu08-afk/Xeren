import React, { useState } from 'react'
import type { UserProfile } from '../../types/auth'
import './AuthDashboardModal.css'

interface AuthDashboardModalProps {
  isOpen: boolean
  onClose: () => void
  currentUser: UserProfile
  onUpdateProfile: (updated: Partial<UserProfile>) => void
  onSocialLogin: (provider: 'google' | 'github' | 'facebook') => void
  onPasskeyAuth: () => Promise<void>
  onRegisterPasskey: (deviceName: string) => Promise<void>
  onSendOtp: (target: string, method: 'email' | 'phone') => Promise<string | undefined>
  onVerifyOtp: (target: string, code: string, method: 'email' | 'phone') => Promise<boolean>
}

export const AuthDashboardModal: React.FC<AuthDashboardModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onUpdateProfile,
  onSocialLogin,
  onPasskeyAuth,
  onRegisterPasskey,
  onSendOtp,
  onVerifyOtp,
}) => {
  const [activeTab, setActiveTab] = useState<'social' | 'email' | 'phone' | 'profile'>('social')

  // Email OTP state
  const [emailInput, setEmailInput] = useState('')
  const [emailCode, setEmailCode] = useState('')
  const [emailOtpSent, setEmailOtpSent] = useState(false)
  const [emailOtpPreview, setEmailOtpPreview] = useState<string | null>(null)
  const [emailError, setEmailError] = useState<string | null>(null)
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null)
  const [isSendingEmail, setIsSendingEmail] = useState(false)

  // Phone OTP state
  const [phoneInput, setPhoneInput] = useState('')
  const [phoneCode, setPhoneCode] = useState('')
  const [phoneOtpSent, setPhoneOtpSent] = useState(false)
  const [phoneOtpPreview, setPhoneOtpPreview] = useState<string | null>(null)
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [phoneSuccess, setPhoneSuccess] = useState<string | null>(null)
  const [isSendingPhone, setIsSendingPhone] = useState(false)

  // Passkey state
  const [passkeyDeviceName, setPasskeyDeviceName] = useState('Windows Hello / Touch ID Key')
  const [passkeyStatus, setPasskeyStatus] = useState<string | null>(null)
  const [isRegisteringPasskey, setIsRegisteringPasskey] = useState(false)

  // Profile edit state
  const [displayName, setDisplayName] = useState(currentUser.display_name)
  const [handle, setHandle] = useState(currentUser.handle)
  const [phoneNumber, setPhoneNumber] = useState(currentUser.phone_number || '')
  const [profileMessage, setProfileMessage] = useState<string | null>(null)

  if (!isOpen) return null

  // --- Handlers ---
  const handleSendEmailOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!emailInput || !emailInput.includes('@')) {
      setEmailError('Please enter a valid email address')
      return
    }
    setEmailError(null)
    setIsSendingEmail(true)
    try {
      const preview = await onSendOtp(emailInput, 'email')
      setEmailOtpSent(true)
      if (preview) setEmailOtpPreview(preview)
      setEmailSuccess(`Verification code dispatched to ${emailInput}`)
    } catch (err: any) {
      setEmailError(err.message || 'Failed to dispatch email verification code')
    } finally {
      setIsSendingEmail(false)
    }
  }

  const handleVerifyEmailOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!emailCode || emailCode.length < 6) {
      setEmailError('Please enter the 6-digit verification code')
      return
    }
    setEmailError(null)
    try {
      const ok = await onVerifyOtp(emailInput, emailCode, 'email')
      if (ok) {
        setEmailSuccess('Email verified successfully! Logged in.')
        setTimeout(() => setActiveTab('profile'), 1200)
      }
    } catch (err: any) {
      setEmailError(err.message || 'Verification failed. Please check code.')
    }
  }

  const handleSendPhoneOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!phoneInput || phoneInput.length < 7) {
      setPhoneError('Please enter a valid phone number with country code')
      return
    }
    setPhoneError(null)
    setIsSendingPhone(true)
    try {
      const preview = await onSendOtp(phoneInput, 'phone')
      setPhoneOtpSent(true)
      if (preview) setPhoneOtpPreview(preview)
      setPhoneSuccess(`Verification SMS dispatched to ${phoneInput}`)
    } catch (err: any) {
      setPhoneError(err.message || 'Failed to dispatch phone verification code')
    } finally {
      setIsSendingPhone(false)
    }
  }

  const handleVerifyPhoneOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!phoneCode || phoneCode.length < 6) {
      setPhoneError('Please enter the 6-digit SMS code')
      return
    }
    setPhoneError(null)
    try {
      const ok = await onVerifyOtp(phoneInput, phoneCode, 'phone')
      if (ok) {
        setPhoneSuccess('Phone verified successfully! Logged in.')
        setTimeout(() => setActiveTab('profile'), 1200)
      }
    } catch (err: any) {
      setPhoneError(err.message || 'Phone verification failed.')
    }
  }

  const handlePasskeyRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setPasskeyStatus('Registering biometric / security key with browser...')
      await onRegisterPasskey(passkeyDeviceName)
      setPasskeyStatus('Passkey registered successfully!')
      setIsRegisteringPasskey(false)
    } catch (err: any) {
      setPasskeyStatus(`Passkey error: ${err.message || 'Registration failed'}`)
    }
  }

  const handlePasskeyAuthenticate = async () => {
    try {
      setPasskeyStatus('Requesting passkey authentication...')
      await onPasskeyAuth()
      setPasskeyStatus('Passkey authenticated successfully!')
    } catch (err: any) {
      setPasskeyStatus(`Authentication error: ${err.message || 'Verification failed'}`)
    }
  }

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault()
    onUpdateProfile({
      display_name: displayName,
      handle: handle.startsWith('@') ? handle : `@${handle}`,
      phone_number: phoneNumber,
    })
    setProfileMessage('Profile updated successfully!')
    setTimeout(() => setProfileMessage(null), 2500)
  }

  return (
    <div
      className="auth-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="User Authentication and Identity Dashboard"
      data-testid="auth-dashboard-modal"
    >
      <div className="auth-modal-window" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <header className="auth-modal-header">
          <div className="auth-modal-header-info">
            <div className="auth-badge-pill">
              <span className="auth-badge-dot" />
              <span>Xeren Identity Gate</span>
            </div>
            <h2 className="auth-modal-title">Sign In & User Details Dashboard</h2>
            <p className="auth-modal-subtitle">
              Unified authentication with Google, GitHub, Facebook, Biometric Passkeys, or Passwordless OTP.
            </p>
          </div>
          <button
            type="button"
            className="auth-modal-close"
            onClick={onClose}
            aria-label="Close Authentication Dashboard"
            data-testid="close-auth-modal"
          >
            ✕
          </button>
        </header>

        {/* Tab Navigation */}
        <nav className="auth-modal-tabs" aria-label="Authentication Options">
          <button
            type="button"
            className={`auth-tab-btn ${activeTab === 'social' ? 'active' : ''}`}
            onClick={() => setActiveTab('social')}
            data-testid="auth-tab-social"
          >
            <span className="tab-icon">⚡</span>
            <span>Social & Passkey</span>
          </button>
          <button
            type="button"
            className={`auth-tab-btn ${activeTab === 'email' ? 'active' : ''}`}
            onClick={() => setActiveTab('email')}
            data-testid="auth-tab-email"
          >
            <span className="tab-icon">✉️</span>
            <span>Code to Email</span>
          </button>
          <button
            type="button"
            className={`auth-tab-btn ${activeTab === 'phone' ? 'active' : ''}`}
            onClick={() => setActiveTab('phone')}
            data-testid="auth-tab-phone"
          >
            <span className="tab-icon">📱</span>
            <span>Code to Phone</span>
          </button>
          <button
            type="button"
            className={`auth-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
            data-testid="auth-tab-profile"
          >
            <span className="tab-icon">👤</span>
            <span>User Details</span>
          </button>
        </nav>

        {/* Body Content */}
        <div className="auth-modal-body">
          {/* TAB 1: Social & Passkey */}
          {activeTab === 'social' && (
            <div className="auth-tab-pane" data-testid="pane-social">
              <div className="auth-providers-list">
                {/* 1. Continue with Google */}
                <button
                  type="button"
                  className="social-auth-btn google-btn"
                  onClick={() => onSocialLogin('google')}
                  data-testid="auth-btn-google"
                >
                  <svg className="social-icon" width="20" height="20" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  <span>Continue with Google</span>
                  <span className="auth-btn-tag">Fast OAuth</span>
                </button>

                {/* 2. Continue with GitHub */}
                <button
                  type="button"
                  className="social-auth-btn github-btn"
                  onClick={() => onSocialLogin('github')}
                  data-testid="auth-btn-github"
                >
                  <svg className="social-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                    />
                  </svg>
                  <span>Continue with GitHub</span>
                  <span className="auth-btn-tag">Developer Auth</span>
                </button>

                {/* 3. Continue with Facebook */}
                <button
                  type="button"
                  className="social-auth-btn facebook-btn"
                  onClick={() => onSocialLogin('facebook')}
                  data-testid="auth-btn-facebook"
                >
                  <svg className="social-icon" width="20" height="20" viewBox="0 0 24 24" fill="#1877F2">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                  </svg>
                  <span>Continue with Facebook</span>
                  <span className="auth-btn-tag">Meta Identity</span>
                </button>

                {/* Divider */}
                <div className="auth-divider">
                  <span>OR USE HARDWARE AUTHENTICATOR</span>
                </div>

                {/* 4. Passkey / Authentication Device */}
                <div className="passkey-action-card">
                  <div className="passkey-card-header">
                    <div className="passkey-icon-wrap">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                        <path d="M12 11c0 3.517-1.009 6.799-2.753 9.571m3.44-2.049A15.938 15.938 0 0 0 14 11c0-4.418-2.686-8-6-8s-6 3.582-6 8c0 2.457 1.077 4.67 2.784 6.273" />
                        <path d="M12.5 18c1.5 0 2.5-1 2.5-2.5V11c0-2.5-1.5-4-3-4" />
                        <circle cx="12" cy="11" r="1" />
                      </svg>
                    </div>
                    <div className="passkey-card-info">
                      <div className="passkey-card-title">Sign in with Passkey / Security Key</div>
                      <div className="passkey-card-desc">
                        FIDO2, Windows Hello, Touch ID, or USB YubiKey without passwords.
                      </div>
                    </div>
                  </div>

                  <div className="passkey-button-group">
                    <button
                      type="button"
                      className="auth-accent-btn"
                      onClick={handlePasskeyAuthenticate}
                      data-testid="auth-btn-passkey"
                    >
                      <span>Unlock with Passkey</span>
                    </button>
                    <button
                      type="button"
                      className="auth-secondary-btn"
                      onClick={() => setIsRegisteringPasskey((prev) => !prev)}
                      data-testid="toggle-register-passkey"
                    >
                      <span>+ Register New Device</span>
                    </button>
                  </div>

                  {/* Passkey Registration Drawer */}
                  {isRegisteringPasskey && (
                    <form className="passkey-register-form" onSubmit={handlePasskeyRegisterSubmit}>
                      <label className="auth-input-label">Device Label</label>
                      <input
                        type="text"
                        className="auth-text-input"
                        value={passkeyDeviceName}
                        onChange={(e) => setPasskeyDeviceName(e.target.value)}
                        placeholder="e.g. Work MacBook Touch ID or YubiKey 5C"
                        data-testid="passkey-device-input"
                      />
                      <button
                        type="submit"
                        className="auth-submit-btn"
                        data-testid="submit-passkey-register"
                      >
                        Create WebAuthn Credential
                      </button>
                    </form>
                  )}

                  {passkeyStatus && <div className="auth-status-banner info">{passkeyStatus}</div>}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Code to Email */}
          {activeTab === 'email' && (
            <div className="auth-tab-pane" data-testid="pane-email">
              <div className="auth-instructions">
                Enter your email address to receive a 6-digit passwordless verification code.
              </div>

              {!emailOtpSent ? (
                <form className="auth-form" onSubmit={handleSendEmailOtp}>
                  <div className="auth-input-group">
                    <label className="auth-input-label" htmlFor="email-otp-field">Email Address</label>
                    <input
                      id="email-otp-field"
                      type="email"
                      className="auth-text-input"
                      placeholder="you@company.com"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      required
                      data-testid="email-otp-input"
                    />
                  </div>

                  {emailError && <div className="auth-status-banner error">{emailError}</div>}

                  <button
                    type="submit"
                    className="auth-submit-btn"
                    disabled={isSendingEmail}
                    data-testid="send-email-otp-btn"
                  >
                    {isSendingEmail ? 'Sending Code...' : 'Send 6-Digit Code'}
                  </button>
                </form>
              ) : (
                <form className="auth-form" onSubmit={handleVerifyEmailOtp}>
                  {emailSuccess && <div className="auth-status-banner success">{emailSuccess}</div>}
                  {emailOtpPreview && (
                    <div className="auth-code-preview" data-testid="email-code-preview">
                      <span className="code-label">Verification Code Preview:</span>
                      <span className="code-value">{emailOtpPreview}</span>
                    </div>
                  )}

                  <div className="auth-input-group">
                    <label className="auth-input-label" htmlFor="email-code-field">Enter 6-Digit Code</label>
                    <input
                      id="email-code-field"
                      type="text"
                      maxLength={6}
                      className="auth-code-input"
                      placeholder="••••••"
                      value={emailCode}
                      onChange={(e) => setEmailCode(e.target.value)}
                      data-testid="email-otp-code-input"
                      autoFocus
                    />
                  </div>

                  {emailError && <div className="auth-status-banner error">{emailError}</div>}

                  <div className="auth-form-buttons">
                    <button
                      type="submit"
                      className="auth-submit-btn"
                      data-testid="verify-email-otp-btn"
                    >
                      Verify & Sign In
                    </button>
                    <button
                      type="button"
                      className="auth-secondary-btn"
                      onClick={() => setEmailOtpSent(false)}
                    >
                      Change Email
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* TAB 3: Code to Phone */}
          {activeTab === 'phone' && (
            <div className="auth-tab-pane" data-testid="pane-phone">
              <div className="auth-instructions">
                Enter your mobile phone number with country code (+1, +44, +91) to receive an SMS verification code.
              </div>

              {!phoneOtpSent ? (
                <form className="auth-form" onSubmit={handleSendPhoneOtp}>
                  <div className="auth-input-group">
                    <label className="auth-input-label" htmlFor="phone-otp-field">Mobile Phone Number</label>
                    <input
                      id="phone-otp-field"
                      type="tel"
                      className="auth-text-input"
                      placeholder="+1 (555) 019-2834"
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value)}
                      required
                      data-testid="phone-otp-input"
                    />
                  </div>

                  {phoneError && <div className="auth-status-banner error">{phoneError}</div>}

                  <button
                    type="submit"
                    className="auth-submit-btn"
                    disabled={isSendingPhone}
                    data-testid="send-phone-otp-btn"
                  >
                    {isSendingPhone ? 'Dispatching SMS...' : 'Send SMS Verification Code'}
                  </button>
                </form>
              ) : (
                <form className="auth-form" onSubmit={handleVerifyPhoneOtp}>
                  {phoneSuccess && <div className="auth-status-banner success">{phoneSuccess}</div>}
                  {phoneOtpPreview && (
                    <div className="auth-code-preview" data-testid="phone-code-preview">
                      <span className="code-label">SMS Code Preview:</span>
                      <span className="code-value">{phoneOtpPreview}</span>
                    </div>
                  )}

                  <div className="auth-input-group">
                    <label className="auth-input-label" htmlFor="phone-code-field">Enter 6-Digit SMS Code</label>
                    <input
                      id="phone-code-field"
                      type="text"
                      maxLength={6}
                      className="auth-code-input"
                      placeholder="••••••"
                      value={phoneCode}
                      onChange={(e) => setPhoneCode(e.target.value)}
                      data-testid="phone-otp-code-input"
                      autoFocus
                    />
                  </div>

                  {phoneError && <div className="auth-status-banner error">{phoneError}</div>}

                  <div className="auth-form-buttons">
                    <button
                      type="submit"
                      className="auth-submit-btn"
                      data-testid="verify-phone-otp-btn"
                    >
                      Verify & Continue
                    </button>
                    <button
                      type="button"
                      className="auth-secondary-btn"
                      onClick={() => setPhoneOtpSent(false)}
                    >
                      Change Phone Number
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* TAB 4: User Details & Profile */}
          {activeTab === 'profile' && (
            <div className="auth-tab-pane" data-testid="pane-profile">
              <div className="profile-card">
                <div className="profile-header-strip">
                  <div className="profile-avatar-wrap">
                    {currentUser.avatar_url ? (
                      <img src={currentUser.avatar_url} alt={currentUser.display_name} className="profile-avatar-img" />
                    ) : (
                      <div className="profile-avatar-fallback">
                        {currentUser.display_name.slice(0, 2).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <div className="profile-strip-meta">
                    <h3 className="profile-name">{currentUser.display_name}</h3>
                    <div className="profile-handle">{currentUser.handle}</div>
                    <span className="profile-tier-badge">{currentUser.plan_tier}</span>
                  </div>
                </div>

                {/* Linked authentication badges */}
                <div className="linked-methods-section">
                  <label className="section-label">Active Authentication Methods</label>
                  <div className="methods-pill-list">
                    {currentUser.linked_methods.map((method) => (
                      <span key={method} className="method-pill" data-testid={`method-pill-${method}`}>
                        <span className="method-pill-dot" />
                        {method.replace('_', ' ').toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Edit Form */}
                <form className="profile-edit-form" onSubmit={handleSaveProfile}>
                  <div className="form-row">
                    <div className="auth-input-group">
                      <label className="auth-input-label">Display Name</label>
                      <input
                        type="text"
                        className="auth-text-input"
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                        data-testid="profile-display-name-input"
                      />
                    </div>
                    <div className="auth-input-group">
                      <label className="auth-input-label">Xeren Handle</label>
                      <input
                        type="text"
                        className="auth-text-input"
                        value={handle}
                        onChange={(e) => setHandle(e.target.value)}
                        data-testid="profile-handle-input"
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="auth-input-group">
                      <label className="auth-input-label">Primary Email</label>
                      <input
                        type="email"
                        className="auth-text-input"
                        value={currentUser.email}
                        disabled
                        title="Linked to primary identity"
                      />
                    </div>
                    <div className="auth-input-group">
                      <label className="auth-input-label">Phone Number</label>
                      <input
                        type="tel"
                        className="auth-text-input"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        placeholder="+1 (555) 019-2834"
                        data-testid="profile-phone-input"
                      />
                    </div>
                  </div>

                  {profileMessage && <div className="auth-status-banner success">{profileMessage}</div>}

                  <button
                    type="submit"
                    className="auth-submit-btn"
                    data-testid="save-profile-btn"
                  >
                    Save Profile Changes
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
