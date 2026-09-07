import React, { useState } from 'react'
import type {
  ProjectType,
  ProjectRole,
  InviteType,
  ProjectCreatePayload,
  Project,
} from '../../types/project'
import type { UserProfile } from '../../types/auth'
import './NewProjectModal.css'

interface PendingDraftInvite {
  id: string
  invite_type: InviteType
  target: string
  role: ProjectRole
  code_preview?: string
  status_label: string
}

interface NewProjectModalProps {
  isOpen: boolean
  onClose: () => void
  currentUser: UserProfile
  onCreateProject: (payload: ProjectCreatePayload) => Promise<Project>
  onInviteMember?: (projectId: string, inviteType: InviteType, target: string, role: ProjectRole) => Promise<any>
}

export const NewProjectModal: React.FC<NewProjectModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onCreateProject,
}) => {
  const [step, setStep] = useState<'select_type' | 'configure'>('select_type')
  const [selectedType, setSelectedType] = useState<ProjectType>('solo')

  // Configuration fields
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [cognitiveMode, setCognitiveMode] = useState<'think' | 'reason' | 'create'>('think')

  // Group Member Invitation State
  const [inviteMethod, setInviteMethod] = useState<'xeren_account' | 'email'>('xeren_account')
  const [xerenHandleInput, setXerenHandleInput] = useState('')
  const [emailInput, setEmailInput] = useState('')
  const [memberRole, setMemberRole] = useState<ProjectRole>('editor')

  // Draft invites list
  const [draftInvites, setDraftInvites] = useState<PendingDraftInvite[]>([])
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null)

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSelectType = (type: ProjectType) => {
    setSelectedType(type)
    setStep('configure')
    if (type === 'solo' && !projectName) {
      setProjectName('Solo Workstation')
    } else if (type === 'group' && !projectName) {
      setProjectName('Collaborative Workspace')
    }
  }

  const handleAddXerenInvite = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanHandle = xerenHandleInput.trim()
    if (!cleanHandle) {
      setInviteError('Please enter a Xeren handle or username (e.g. @sarah_ai)')
      return
    }

    const formatted = cleanHandle.startsWith('@') ? cleanHandle : `@${cleanHandle}`
    if (draftInvites.some((i) => i.target.toLowerCase() === formatted.toLowerCase())) {
      setInviteError(`${formatted} is already in the invitation list`)
      return
    }

    setInviteError(null)
    const newInvite: PendingDraftInvite = {
      id: `draft_${Date.now()}_${Math.random()}`,
      invite_type: 'xeren_account',
      target: formatted,
      role: memberRole,
      status_label: 'In-App Notification Queued (Real-time)',
    }
    setDraftInvites((prev) => [...prev, newInvite])
    setXerenHandleInput('')
    setInviteSuccess(`Notification will be dispatched to ${formatted}. When accepted, they join automatically.`)
    setTimeout(() => setInviteSuccess(null), 3500)
  }

  const handleAddEmailInvite = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanEmail = emailInput.trim()
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setInviteError('Please enter a valid email address (e.g. colleague@company.com)')
      return
    }

    if (draftInvites.some((i) => i.target.toLowerCase() === cleanEmail.toLowerCase())) {
      setInviteError(`${cleanEmail} is already in the invitation list`)
      return
    }

    setInviteError(null)
    const mockCode = `${Math.floor(100000 + Math.random() * 900000)}`
    const newInvite: PendingDraftInvite = {
      id: `draft_${Date.now()}_${Math.random()}`,
      invite_type: 'email',
      target: cleanEmail,
      role: memberRole,
      code_preview: mockCode,
      status_label: `Email Verification Link (Code: ${mockCode}) & Download Guide`,
    }
    setDraftInvites((prev) => [...prev, newInvite])
    setEmailInput('')
    setInviteSuccess(`Invitation verification email generated for ${cleanEmail} with Xeren download instructions.`)
    setTimeout(() => setInviteSuccess(null), 3500)
  }

  const handleRemoveDraftInvite = (id: string) => {
    setDraftInvites((prev) => prev.filter((i) => i.id !== id))
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!projectName.trim()) {
      setErrorMessage('Please enter a project name')
      return
    }

    setErrorMessage(null)
    setIsSubmitting(true)
    try {
      const payload: ProjectCreatePayload = {
        name: projectName.trim(),
        description: projectDescription.trim(),
        project_type: selectedType,
        tags: [selectedType, cognitiveMode],
        initial_invites: draftInvites.map((i) => ({
          project_id: '',
          invite_type: i.invite_type,
          target: i.target,
          role: i.role,
        })),
      }

      await onCreateProject(payload)
      onClose()
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to initialize project')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="project-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Create New Project"
      data-testid="new-project-modal"
    >
      <div className="project-modal-window" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <header className="project-modal-header">
          <div className="project-modal-header-meta">
            <span className="project-header-pill">Workspace Genesis</span>
            <h2 className="project-modal-title">
              {step === 'select_type' ? 'Start a New Project' : `Configure ${selectedType === 'solo' ? 'Solo' : 'Group'} Project`}
            </h2>
            <p className="project-modal-subtitle">
              {step === 'select_type'
                ? 'Choose between an isolated solo workstation or a collaborative multi-member workspace.'
                : selectedType === 'solo'
                ? 'Private workstation for single-developer deep work, automated research, and offline execution.'
                : 'Multi-member workspace with real-time peer sync and Xeren / email invitation onboarding.'}
            </p>
          </div>
          <button
            type="button"
            className="project-modal-close"
            onClick={onClose}
            aria-label="Close modal"
            data-testid="close-project-modal"
          >
            ✕
          </button>
        </header>

        {/* STEP 1: SELECT SOLO VS GROUP */}
        {step === 'select_type' && (
          <div className="project-type-selection-body" data-testid="project-type-selection">
            <div className="project-type-cards-grid">
              {/* Solo Project Card */}
              <div
                className="project-type-card solo-card"
                onClick={() => handleSelectType('solo')}
                role="button"
                tabIndex={0}
                data-testid="project-type-solo"
              >
                <div className="card-top-icon-wrap solo-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <div className="card-tag">Single Developer</div>
                <h3 className="card-title">Solo Project</h3>
                <p className="card-desc">
                  An isolated, private workstation designed for deep strawberry chain-of-thought research, personal
                  coding synthesis, and zero-leakage local execution.
                </p>
                <ul className="card-features">
                  <li>
                    <span className="feat-check">✓</span> 100% Isolated Local Storage & Hardware Vault
                  </li>
                  <li>
                    <span className="feat-check">✓</span> Instant Zero-Config Setup
                  </li>
                  <li>
                    <span className="feat-check">✓</span> Deep Autonomous Research & Freelance Mode
                  </li>
                </ul>
                <button
                  type="button"
                  className="card-select-btn"
                  onClick={() => handleSelectType('solo')}
                  data-testid="select-solo-btn"
                >
                  Create Solo Project →
                </button>
              </div>

              {/* Group Project Card */}
              <div
                className="project-type-card group-card"
                onClick={() => handleSelectType('group')}
                role="button"
                tabIndex={0}
                data-testid="project-type-group"
              >
                <div className="card-top-icon-wrap group-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </div>
                <div className="card-tag group-tag">Multi-Member Team</div>
                <h3 className="card-title">Group Project</h3>
                <p className="card-desc">
                  A real-time collaborative workspace. Invite teammates via their Xeren accounts or emails with
                  interactive in-app notifications and verification codes.
                </p>
                <ul className="card-features">
                  <li>
                    <span className="feat-check group-check">✓</span> Add Members via Xeren Handle or Email
                  </li>
                  <li>
                    <span className="feat-check group-check">✓</span> Real-Time Notification & One-Click Accept
                  </li>
                  <li>
                    <span className="feat-check group-check">✓</span> Role-Based Access: Admin, Editor, Reviewer, Viewer
                  </li>
                </ul>
                <button
                  type="button"
                  className="card-select-btn group-btn"
                  onClick={() => handleSelectType('group')}
                  data-testid="select-group-btn"
                >
                  Create Group Project →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: CONFIGURE PROJECT & INVITE MEMBERS */}
        {step === 'configure' && (
          <form className="project-config-form" onSubmit={handleCreateSubmit} data-testid="project-config-form">
            <div className="config-scroll-area">
              {/* Back to type selector */}
              <button
                type="button"
                className="back-type-btn"
                onClick={() => setStep('select_type')}
                data-testid="back-to-type-btn"
              >
                ← Switch Project Type ({selectedType.toUpperCase()})
              </button>

              {/* Basic Details */}
              <div className="form-section">
                <label className="config-label">Project Name *</label>
                <input
                  type="text"
                  className="config-text-input"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder={selectedType === 'solo' ? 'e.g. Strawberry Deep Research' : 'e.g. Autonomous AI Engine'}
                  required
                  data-testid="project-name-input"
                />
              </div>

              <div className="form-section">
                <label className="config-label">Objective & Summary</label>
                <textarea
                  className="config-textarea"
                  value={projectDescription}
                  onChange={(e) => setProjectDescription(e.target.value)}
                  placeholder="Describe the primary goals, tech stack, and deliverable targets for this workspace..."
                  rows={2}
                  data-testid="project-desc-input"
                />
              </div>

              {/* Solo Specific: Cognitive Mode */}
              {selectedType === 'solo' && (
                <div className="form-section">
                  <label className="config-label">Primary Cognitive Mode</label>
                  <div className="mode-selector-grid">
                    <button
                      type="button"
                      className={`mode-pick-btn ${cognitiveMode === 'think' ? 'active' : ''}`}
                      onClick={() => setCognitiveMode('think')}
                    >
                      <span className="mode-name">Think</span>
                      <span className="mode-sub">Deep Chain-of-Thought</span>
                    </button>
                    <button
                      type="button"
                      className={`mode-pick-btn ${cognitiveMode === 'reason' ? 'active' : ''}`}
                      onClick={() => setCognitiveMode('reason')}
                    >
                      <span className="mode-name">Reason</span>
                      <span className="mode-sub">Rapid Tool Execution</span>
                    </button>
                    <button
                      type="button"
                      className={`mode-pick-btn ${cognitiveMode === 'create' ? 'active' : ''}`}
                      onClick={() => setCognitiveMode('create')}
                    >
                      <span className="mode-name">Create</span>
                      <span className="mode-sub">Deliverable Packaging</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Group Specific: Member Invitation Section */}
              {selectedType === 'group' && (
                <div className="form-section group-invitation-container" data-testid="group-invitation-section">
                  <div className="invitation-header">
                    <h4 className="invitation-title">Add Project Members</h4>
                    <p className="invitation-subtitle">
                      Invite teammates via their Xeren handle (instant in-app notification) or their email address.
                    </p>
                  </div>

                  {/* Dual Invitation Method Selector */}
                  <div className="invite-method-tabs">
                    <button
                      type="button"
                      className={`invite-tab-btn ${inviteMethod === 'xeren_account' ? 'active' : ''}`}
                      onClick={() => setInviteMethod('xeren_account')}
                      data-testid="tab-invite-xeren"
                    >
                      <span className="method-icon">🪐</span>
                      <span>Add via Xeren Account</span>
                    </button>
                    <button
                      type="button"
                      className={`invite-tab-btn ${inviteMethod === 'email' ? 'active' : ''}`}
                      onClick={() => setInviteMethod('email')}
                      data-testid="tab-invite-email"
                    >
                      <span className="method-icon">📧</span>
                      <span>Add via Email Account</span>
                    </button>
                  </div>

                  {/* Sub-Form: Xeren Account */}
                  {inviteMethod === 'xeren_account' && (
                    <div className="invite-subform" data-testid="xeren-invite-form">
                      <div className="invite-input-row">
                        <div className="invite-input-group flex-2">
                          <label className="invite-label">Xeren Handle / Username</label>
                          <input
                            type="text"
                            className="config-text-input"
                            value={xerenHandleInput}
                            onChange={(e) => setXerenHandleInput(e.target.value)}
                            placeholder="@username or handle (e.g. @sarah_ai, @dev_lead)"
                            data-testid="invite-xeren-handle-input"
                          />
                        </div>
                        <div className="invite-input-group flex-1">
                          <label className="invite-label">Role</label>
                          <select
                            className="config-select"
                            value={memberRole}
                            onChange={(e) => setMemberRole(e.target.value as ProjectRole)}
                            data-testid="invite-role-select"
                          >
                            <option value="editor">Editor (Write & Execute)</option>
                            <option value="reviewer">Reviewer (Suggest & Validate)</option>
                            <option value="viewer">Viewer (Read Only)</option>
                            <option value="admin">Admin (Full Control)</option>
                          </select>
                        </div>
                        <button
                          type="button"
                          className="invite-action-btn"
                          onClick={handleAddXerenInvite}
                          data-testid="send-xeren-invite-btn"
                        >
                          + Send In-App Invite
                        </button>
                      </div>
                      <div className="invite-hint-banner">
                        🔔 The invitee receives an interactive notification in their Xeren notification bell with
                        Accept/Decline buttons. Upon accepting, they instantly join the group project.
                      </div>
                    </div>
                  )}

                  {/* Sub-Form: Email Account */}
                  {inviteMethod === 'email' && (
                    <div className="invite-subform" data-testid="email-invite-form">
                      <div className="invite-input-row">
                        <div className="invite-input-group flex-2">
                          <label className="invite-label">Member Email Address</label>
                          <input
                            type="email"
                            className="config-text-input"
                            value={emailInput}
                            onChange={(e) => setEmailInput(e.target.value)}
                            placeholder="colleague@organization.com"
                            data-testid="invite-email-input"
                          />
                        </div>
                        <div className="invite-input-group flex-1">
                          <label className="invite-label">Role</label>
                          <select
                            className="config-select"
                            value={memberRole}
                            onChange={(e) => setMemberRole(e.target.value as ProjectRole)}
                          >
                            <option value="editor">Editor</option>
                            <option value="viewer">Viewer</option>
                            <option value="reviewer">Reviewer</option>
                          </select>
                        </div>
                        <button
                          type="button"
                          className="invite-action-btn email-variant"
                          onClick={handleAddEmailInvite}
                          data-testid="send-email-invite-btn"
                        >
                          + Send Email Verification
                        </button>
                      </div>
                      <div className="invite-hint-banner">
                        ✉️ An email verification code and invitation link are generated. Recipient downloads/opens
                        Xeren and enters the verification code to join.
                      </div>
                    </div>
                  )}

                  {inviteError && <div className="invite-status-msg error">{inviteError}</div>}
                  {inviteSuccess && <div className="invite-status-msg success">{inviteSuccess}</div>}

                  {/* Members & Invites Table */}
                  <div className="project-members-table-wrap">
                    <label className="config-label">
                      Workspace Members & Queued Invites ({1 + draftInvites.length})
                    </label>
                    <div className="members-list-card" data-testid="project-members-table">
                      {/* Owner Row */}
                      <div className="member-row owner-row">
                        <div className="member-avatar-chip">
                          {currentUser.display_name.slice(0, 2).toUpperCase()}
                        </div>
                        <div className="member-info">
                          <div className="member-name-line">
                            <span className="member-name">{currentUser.display_name}</span>
                            <span className="member-handle">{currentUser.handle}</span>
                            <span className="owner-badge">PROJECT OWNER</span>
                          </div>
                          <span className="member-sub">{currentUser.email}</span>
                        </div>
                      </div>

                      {/* Queued Draft Invites */}
                      {draftInvites.map((inv) => (
                        <div key={inv.id} className="member-row invite-row" data-testid={`draft-invite-row-${inv.id}`}>
                          <div className="member-avatar-chip invite-avatar">
                            {inv.invite_type === 'xeren_account' ? 'XR' : '✉️'}
                          </div>
                          <div className="member-info">
                            <div className="member-name-line">
                              <span className="member-name">{inv.target}</span>
                              <span className="role-tag">{inv.role.toUpperCase()}</span>
                              <span className="invite-status-badge">{inv.status_label}</span>
                            </div>
                            <span className="member-sub">
                              Type: {inv.invite_type === 'xeren_account' ? 'Xeren Account Notification' : 'Email Verification Link'}
                            </span>
                          </div>
                          <button
                            type="button"
                            className="remove-invite-btn"
                            onClick={() => handleRemoveDraftInvite(inv.id)}
                            title="Remove invitation"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {errorMessage && <div className="project-error-banner">{errorMessage}</div>}
            </div>

            {/* Form Footer Action */}
            <div className="project-modal-footer">
              <button
                type="button"
                className="cancel-btn"
                onClick={onClose}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="launch-project-btn"
                disabled={isSubmitting}
                data-testid={selectedType === 'solo' ? 'create-solo-project-btn' : 'create-group-project-btn'}
              >
                {isSubmitting
                  ? 'Initializing...'
                  : selectedType === 'solo'
                  ? '⚡ Create Solo Workspace'
                  : `🚀 Launch Group Project (${1 + draftInvites.length} Members)`}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
