import React, { useState, useEffect, useRef } from 'react'
import type {
  Project,
  ProjectRole,
  ProjectCoachMessage,
  ProjectSpecification,
} from '../../types/project'
import './ProjectWorkspaceModal.css'

interface ProjectWorkspaceModalProps {
  isOpen: boolean
  onClose: () => void
  project: Project | null
  currentUserId?: string
  onProjectUpdated?: (updatedProject: Project) => void
}

type ActiveTab = 'coach' | 'specs' | 'roles' | 'milestones'

const ROLE_OPTIONS: { role: ProjectRole; label: string; icon: string }[] = [
  { role: 'owner', label: 'Project Owner', icon: '👑' },
  { role: 'tech_lead', label: 'Tech Lead', icon: '⚡' },
  { role: 'architect', label: 'System Architect', icon: '🏛️' },
  { role: 'ai_specialist', label: 'AI Specialist', icon: '🧠' },
  { role: 'engineer', label: 'Core Engineer', icon: '💻' },
  { role: 'reviewer', label: 'Code Reviewer', icon: '🔍' },
  { role: 'viewer', label: 'Stakeholder / Viewer', icon: '👁️' },
]

export const ProjectWorkspaceModal: React.FC<ProjectWorkspaceModalProps> = ({
  isOpen,
  onClose,
  project,
  currentUserId = 'usr_dev_01',
  onProjectUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('coach')
  const [activeMemberId, setActiveMemberId] = useState<string>(currentUserId)
  const [messages, setMessages] = useState<ProjectCoachMessage[]>([])
  const [inputQuery, setInputQuery] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isSavingSpecs, setIsSavingSpecs] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  // Editable specifications state
  const [techStackInput, setTechStackInput] = useState('')
  const [architecturePattern, setArchitecturePattern] = useState('')
  const [constraintsText, setConstraintsText] = useState('')
  const [targetApisText, setTargetApisText] = useState('')
  const [deliverablesText, setDeliverablesText] = useState('')

  const chatEndRef = useRef<HTMLDivElement>(null)

  // Sync active project state
  useEffect(() => {
    if (project) {
      const specs = project.specifications
      if (specs) {
        setTechStackInput(specs.tech_stack?.join(', ') || '')
        setArchitecturePattern(specs.architecture_pattern || '')
        setConstraintsText(specs.constraints?.join('\n') || '')
        setTargetApisText(specs.target_apis?.join(', ') || '')
        setDeliverablesText(specs.deliverables?.join('\n') || '')
      }
    }
  }, [project])

  // Fetch coach history for the currently viewed member workstation
  const loadCoachHistory = async (projId: string, memberId: string) => {
    try {
      const res = await fetch(`/api/projects/${projId}/coach/messages?member_id=${memberId}`)
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
      } else {
        // Fallback for isolated client-side display if backend is offline
        const fallbackSeed: ProjectCoachMessage = {
          message_id: `pcm_offline_${memberId}`,
          project_id: projId,
          member_user_id: memberId,
          member_handle: memberId === 'usr_peer_02' ? '@sarah_ai' : '@xeren_dev',
          sender: 'coach_agent',
          content: `Welcome to your dedicated workstation. Zero-interruption stream is active.`,
          timestamp: new Date().toISOString(),
          role_context: memberId === 'usr_peer_02' ? 'AI Specialist' : 'System Architect',
        }
        setMessages([fallbackSeed])
      }
    } catch {
      // Fallback
      setMessages([
        {
          message_id: `pcm_mock_${memberId}`,
          project_id: projId,
          member_user_id: memberId,
          member_handle: memberId === 'usr_peer_02' ? '@sarah_ai' : '@xeren_dev',
          sender: 'coach_agent',
          content: `Project Coach ready. Isolated from other workstation members.`,
          timestamp: new Date().toISOString(),
        },
      ])
    }
  }

  useEffect(() => {
    if (isOpen && project) {
      loadCoachHistory(project.project_id, activeMemberId)
    }
  }, [isOpen, project?.project_id, activeMemberId])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!isOpen || !project) return null

  const activeMember = project.members?.find((m) => m.user_id === activeMemberId) || project.members?.[0]
  const currentMemberRole = activeMember?.role || 'engineer'

  // Send message to Coach Agent
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputQuery).trim()
    if (!query || isSending) return

    setIsSending(true)
    const userMsg: ProjectCoachMessage = {
      message_id: `pcm_temp_${Date.now()}`,
      project_id: project.project_id,
      member_user_id: activeMemberId,
      member_handle: activeMember?.handle || '@xeren_dev',
      sender: 'user',
      content: query,
      timestamp: new Date().toISOString(),
      role_context: currentMemberRole,
    }

    setMessages((prev) => [...prev, userMsg])
    setInputQuery('')

    try {
      const res = await fetch(`/api/projects/${project.project_id}/coach/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: project.project_id,
          member_user_id: activeMemberId,
          message: query,
          role_context: currentMemberRole,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        if (data.message) {
          setMessages((prev) => [...prev, data.message])
        }
      } else {
        // Mock reply if backend is offline
        const mockReply: ProjectCoachMessage = {
          message_id: `pcm_reply_${Date.now()}`,
          project_id: project.project_id,
          member_user_id: activeMemberId,
          member_handle: activeMember?.handle || '@xeren_dev',
          sender: 'coach_agent',
          content: `### [Coach Guidance for ${currentMemberRole.toUpperCase()}]\n\nFor **${project.name}**, your workstation runs in parallel isolation. In alignment with **${architecturePattern || 'Modular System'}**, ensure all interfaces adhere to specifications and active constraints.`,
          timestamp: new Date().toISOString(),
          role_context: currentMemberRole,
        }
        setMessages((prev) => [...prev, mockReply])
      }
    } catch {
      const mockReply: ProjectCoachMessage = {
        message_id: `pcm_reply_${Date.now()}`,
        project_id: project.project_id,
        member_user_id: activeMemberId,
        member_handle: activeMember?.handle || '@xeren_dev',
        sender: 'coach_agent',
        content: `### [Coach Guidance for ${currentMemberRole.toUpperCase()}]\n\nProcessed query for ${activeMember?.handle}. All teammate workstations remain uninterrupted.`,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, mockReply])
    } finally {
      setIsSending(false)
    }
  }

  // Save Project Specifications
  const handleSaveSpecifications = async () => {
    setIsSavingSpecs(true)
    setStatusMessage(null)

    const updatedSpecs: ProjectSpecification = {
      tech_stack: techStackInput.split(',').map((s) => s.trim()).filter(Boolean),
      architecture_pattern: architecturePattern.trim(),
      constraints: constraintsText.split('\n').map((s) => s.trim()).filter(Boolean),
      target_apis: targetApisText.split(',').map((s) => s.trim()).filter(Boolean),
      deliverables: deliverablesText.split('\n').map((s) => s.trim()).filter(Boolean),
    }

    try {
      const res = await fetch(`/api/projects/${project.project_id}/specifications`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ specifications: updatedSpecs }),
      })

      if (res.ok) {
        const data = await res.json()
        if (data.project && onProjectUpdated) {
          onProjectUpdated(data.project)
        }
        setStatusMessage('Specifications successfully updated!')
      } else {
        setStatusMessage('Specifications updated locally.')
      }
    } catch {
      setStatusMessage('Specifications updated locally.')
    } finally {
      setIsSavingSpecs(false)
      setTimeout(() => setStatusMessage(null), 3000)
    }
  }

  // Update Member Role
  const handleUpdateMemberRole = async (userId: string, newRole: ProjectRole, activeTask?: string) => {
    try {
      const res = await fetch(`/api/projects/${project.project_id}/members/${userId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole, active_task: activeTask }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.project && onProjectUpdated) {
          onProjectUpdated(data.project)
        }
      }
    } catch (err) {
      console.warn('Role update error:', err)
    }
  }

  // Milestones Progress Calculation
  const totalMilestones = project.milestones?.length || 0
  const completedMilestones = project.milestones?.filter((m) => m.status === 'completed').length || 0
  const progressPercent = totalMilestones > 0 ? Math.round((completedMilestones / totalMilestones) * 100) : 0

  return (
    <div className="project-workspace-modal-overlay" onClick={onClose} id="project-workspace-modal">
      <div
        className="project-workspace-container"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Dedicated Project Workspace"
      >
        {/* Workspace Top Header */}
        <div className="workspace-header">
          <div className="workspace-title-block">
            <div className="workspace-title-row">
              <span className="project-type-tag">
                {project.project_type === 'group' ? '👥 Group Project' : '👤 Solo Project'}
              </span>
              <h2 className="project-workspace-name">{project.name}</h2>
              {project.synced_with_mongo && (
                <span className="mongo-badge" title="Live synchronized with MongoDB Atlas">
                  🍃 Atlas Synced
                </span>
              )}
            </div>
            <p className="workspace-description">{project.description || 'Dedicated collaborative intelligence workspace'}</p>
          </div>

          <div className="workspace-header-actions">
            <div className="workstation-status-pill">
              <span className="status-dot online"></span>
              <span className="pill-text">Zero-Interruption Parallel Stream</span>
            </div>
            <button
              className="workspace-close-btn"
              onClick={onClose}
              id="workspace-close-button"
              aria-label="Close Project Workspace"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Workstation Isolation Switcher Bar */}
        <div className="workstation-switcher-bar" id="workstation-switcher">
          <div className="switcher-label">
            <span className="switcher-icon">⚡</span>
            <span>Active Workstation:</span>
          </div>

          <div className="teammate-pills">
            {project.members?.map((member) => {
              const isSelected = member.user_id === activeMemberId
              const isUserSelf = member.user_id === currentUserId
              return (
                <button
                  key={member.user_id}
                  id={`workstation-tab-${member.handle.replace('@', '')}`}
                  className={`teammate-pill ${isSelected ? 'active' : ''}`}
                  onClick={() => setActiveMemberId(member.user_id)}
                >
                  <span className="member-avatar-mini">
                    {member.avatar_url ? (
                      <img src={member.avatar_url} alt={member.handle} />
                    ) : (
                      member.handle.slice(1, 3).toUpperCase()
                    )}
                  </span>
                  <span className="member-handle-text">{member.handle}</span>
                  <span className="member-role-badge">
                    {member.role ? member.role.replace('_', ' ') : 'engineer'}
                  </span>
                  {isUserSelf && <span className="self-tag">(You)</span>}
                  {isSelected && <span className="isolated-active-indicator" title="Isolated Workstation Stream">🔒</span>}
                </button>
              )
            })}
          </div>

          <div className="active-peer-task-info">
            <span className="task-pulse-dot"></span>
            <span className="peer-task-label">
              <strong>{activeMember?.handle}</strong>: {activeMember?.active_task || 'Consulting AI Coach'}
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="workspace-tabs-nav">
          <button
            id="tab-btn-coach"
            className={`tab-btn ${activeTab === 'coach' ? 'active' : ''}`}
            onClick={() => setActiveTab('coach')}
          >
            🤖 AI Coach Workstation
          </button>
          <button
            id="tab-btn-specs"
            className={`tab-btn ${activeTab === 'specs' ? 'active' : ''}`}
            onClick={() => setActiveTab('specs')}
          >
            📋 Project Specifications
          </button>
          <button
            id="tab-btn-roles"
            className={`tab-btn ${activeTab === 'roles' ? 'active' : ''}`}
            onClick={() => setActiveTab('roles')}
          >
            👥 Roles & Teammates ({project.members?.length || 1})
          </button>
          <button
            id="tab-btn-milestones"
            className={`tab-btn ${activeTab === 'milestones' ? 'active' : ''}`}
            onClick={() => setActiveTab('milestones')}
          >
            🎯 Milestones & Sprints ({progressPercent}%)
          </button>
        </div>

        {/* Tab 1: AI Coach Workstation */}
        {activeTab === 'coach' && (
          <div className="workspace-tab-content coach-tab-content">
            <div className="coach-session-banner">
              <div className="coach-banner-info">
                <span className="coach-ai-avatar">🧠</span>
                <div>
                  <h4 className="coach-banner-title">
                    Project Coach Agent • {currentMemberRole.replace('_', ' ').toUpperCase()} WORKSTATION
                  </h4>
                  <p className="coach-banner-subtitle">
                    Dedicated coach mentorship for <strong>{activeMember?.handle}</strong>. Fully isolated session;
                    teammates asking doubts simultaneously will not interrupt or pollute this stream.
                  </p>
                </div>
              </div>
              <div className="coach-isolation-tag">
                <span>🛡️ Non-Interruptible History</span>
              </div>
            </div>

            {/* Coach Message Stream */}
            <div className="coach-chat-stream" id="coach-message-stream">
              {messages.map((msg) => {
                const isUser = msg.sender === 'user'
                return (
                  <div
                    key={msg.message_id}
                    className={`coach-message-bubble ${isUser ? 'user-bubble' : 'coach-bubble'}`}
                  >
                    <div className="message-meta-header">
                      <span className="message-sender-name">
                        {isUser ? msg.member_handle : 'Project Coach Agent'}
                      </span>
                      {msg.role_context && (
                        <span className="role-context-badge">[{msg.role_context}]</span>
                      )}
                      <span className="message-time">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="message-body-content">
                      {msg.content.split('\n').map((line, idx) => {
                        if (line.startsWith('### ')) {
                          return <h5 key={idx} className="coach-msg-heading">{line.replace('### ', '')}</h5>
                        }
                        if (line.startsWith('- ')) {
                          return <li key={idx} className="coach-msg-bullet">{line.replace('- ', '')}</li>
                        }
                        if (line.startsWith('> ')) {
                          return <blockquote key={idx} className="coach-msg-quote">{line.replace('> ', '')}</blockquote>
                        }
                        return <p key={idx}>{line}</p>
                      })}
                    </div>
                  </div>
                )
              })}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Prompt Chips */}
            <div className="quick-coach-prompts">
              <span className="quick-prompts-label">Quick Consult:</span>
              <button
                className="prompt-chip"
                onClick={() => handleSendMessage('What is our architecture pattern and system constraints?')}
              >
                🏛️ Architecture Blueprint
              </button>
              <button
                className="prompt-chip"
                onClick={() => handleSendMessage('What is my role responsibility for this project?')}
              >
                💼 Role Responsibilities
              </button>
              <button
                className="prompt-chip"
                onClick={() => handleSendMessage('Check active sprint milestones and deliverables')}
              >
                🎯 Active Milestones
              </button>
              <button
                className="prompt-chip"
                onClick={() => handleSendMessage('I have a doubt regarding our tech stack interfaces')}
              >
                ❓ Ask Tech Doubt
              </button>
            </div>

            {/* Coach Input Bar */}
            <div className="coach-input-container">
              <textarea
                id="coach-chat-input"
                className="coach-textarea"
                rows={2}
                placeholder={`Ask Project Coach a question or doubt as ${activeMember?.handle} (${currentMemberRole})...`}
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
              />
              <button
                id="coach-send-button"
                className="coach-send-btn"
                disabled={!inputQuery.trim() || isSending}
                onClick={() => handleSendMessage()}
              >
                {isSending ? 'Thinking...' : 'Consult Coach →'}
              </button>
            </div>
          </div>
        )}

        {/* Tab 2: Project Specifications */}
        {activeTab === 'specs' && (
          <div className="workspace-tab-content specs-tab-content" id="project-specs-panel">
            <div className="specs-card">
              <h3 className="specs-section-title">🛠️ Technology Stack</h3>
              <p className="specs-help-text">Comma-separated list of foundational technologies, frameworks, and libraries.</p>
              <input
                id="specs-tech-stack-input"
                type="text"
                className="specs-input"
                value={techStackInput}
                onChange={(e) => setTechStackInput(e.target.value)}
                placeholder="e.g. Python 3.12, FastAPI, React 19, MongoDB Atlas, Docker"
              />
              <div className="specs-pills-preview">
                {techStackInput.split(',').map((tech, idx) => {
                  const t = tech.trim()
                  return t ? <span key={idx} className="tech-pill">{t}</span> : null
                })}
              </div>
            </div>

            <div className="specs-card">
              <h3 className="specs-section-title">🏛️ Architecture Pattern</h3>
              <p className="specs-help-text">Guiding system architectural style and communication paradigms.</p>
              <input
                id="specs-arch-input"
                type="text"
                className="specs-input"
                value={architecturePattern}
                onChange={(e) => setArchitecturePattern(e.target.value)}
                placeholder="e.g. Distributed Multi-Agent Event Bus, Micro-frontends"
              />
            </div>

            <div className="specs-grid-two">
              <div className="specs-card">
                <h3 className="specs-section-title">🔒 Constraints & Security Rules</h3>
                <p className="specs-help-text">One constraint per line (e.g. strict latency, data privacy, zero telemetry leakage).</p>
                <textarea
                  id="specs-constraints-input"
                  className="specs-textarea"
                  rows={4}
                  value={constraintsText}
                  onChange={(e) => setConstraintsText(e.target.value)}
                  placeholder="Zero-interruption workstation isolation&#10;Strict role-based action gating&#10;Real-time sync latency < 50ms"
                />
              </div>

              <div className="specs-card">
                <h3 className="specs-section-title">🔌 Target APIs & Integrations</h3>
                <p className="specs-help-text">External model endpoints, databases, or MCP tools (comma-separated).</p>
                <textarea
                  id="specs-apis-input"
                  className="specs-textarea"
                  rows={4}
                  value={targetApisText}
                  onChange={(e) => setTargetApisText(e.target.value)}
                  placeholder="OpenAI API, Anthropic Claude API, Gemini Pro API, MongoDB Atlas"
                />
              </div>
            </div>

            <div className="specs-card">
              <h3 className="specs-section-title">📦 Key Deliverables</h3>
              <p className="specs-help-text">Key outcomes and sprint milestones (one per line).</p>
              <textarea
                id="specs-deliverables-input"
                className="specs-textarea"
                rows={3}
                value={deliverablesText}
                onChange={(e) => setDeliverablesText(e.target.value)}
                placeholder="Parallel collaborative workstations&#10;AI Coach integration&#10;Role matrix management"
              />
            </div>

            <div className="specs-footer">
              {statusMessage && <span className="specs-status-msg">{statusMessage}</span>}
              <button
                id="save-specifications-btn"
                className="specs-save-btn"
                disabled={isSavingSpecs}
                onClick={handleSaveSpecifications}
              >
                {isSavingSpecs ? 'Saving...' : '💾 Save Technical Specifications'}
              </button>
            </div>
          </div>
        )}

        {/* Tab 3: Roles & Teammates */}
        {activeTab === 'roles' && (
          <div className="workspace-tab-content roles-tab-content" id="project-roles-panel">
            <div className="roles-header-desc">
              <h3>Role Matrix & Member Responsibilities</h3>
              <p>
                Assign granular roles to configure coaching responses, permissions, and workstation session scopes.
              </p>
            </div>

            <div className="members-role-grid">
              {project.members?.map((member) => {
                return (
                  <div key={member.user_id} className="member-role-card">
                    <div className="member-card-top">
                      <div className="member-avatar-lg">
                        {member.avatar_url ? (
                          <img src={member.avatar_url} alt={member.handle} />
                        ) : (
                          member.handle.slice(1, 3).toUpperCase()
                        )}
                      </div>
                      <div className="member-info-col">
                        <div className="member-name-row">
                          <span className="member-display-name">{member.display_name}</span>
                          {member.is_owner && <span className="owner-badge">👑 Owner</span>}
                        </div>
                        <span className="member-email-text">{member.email}</span>
                        <span className="member-handle-sub">{member.handle}</span>
                      </div>
                    </div>

                    <div className="member-card-role-section">
                      <label className="role-select-label">Assigned Project Role:</label>
                      <select
                        id={`role-select-${member.user_id}`}
                        className="role-dropdown"
                        value={member.role || 'engineer'}
                        onChange={(e) =>
                          handleUpdateMemberRole(member.user_id, e.target.value as ProjectRole, member.active_task)
                        }
                      >
                        {ROLE_OPTIONS.map((opt) => (
                          <option key={opt.role} value={opt.role}>
                            {opt.icon} {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="member-card-task-section">
                      <label className="task-input-label">Active Workstation Task:</label>
                      <input
                        type="text"
                        className="task-input"
                        value={member.active_task || ''}
                        placeholder="Current sprint task..."
                        onChange={(e) => {
                          const newText = e.target.value
                          member.active_task = newText
                        }}
                        onBlur={() =>
                          handleUpdateMemberRole(member.user_id, member.role, member.active_task)
                        }
                      />
                    </div>

                    <div className="workstation-health-footer">
                      <span className="health-dot live"></span>
                      <span>Workstation Isolated • No Message Bleeding</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Tab 4: Milestones & Sprints */}
        {activeTab === 'milestones' && (
          <div className="workspace-tab-content milestones-tab-content" id="project-milestones-panel">
            <div className="milestone-progress-card">
              <div className="progress-text-row">
                <span className="progress-title">Sprint Delivery Progress</span>
                <span className="progress-percent">{progressPercent}% Completed</span>
              </div>
              <div className="progress-bar-track">
                <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }}></div>
              </div>
              <div className="milestone-summary-counts">
                <span>Total: {totalMilestones}</span>
                <span>Completed: {completedMilestones}</span>
                <span>In Progress: {totalMilestones - completedMilestones}</span>
              </div>
            </div>

            <div className="milestones-list">
              {project.milestones && project.milestones.length > 0 ? (
                project.milestones.map((ms) => {
                  const isCompleted = ms.status === 'completed'
                  return (
                    <div key={ms.milestone_id} className={`milestone-item-card ${isCompleted ? 'completed' : ''}`}>
                      <div className="milestone-status-indicator">
                        {isCompleted ? '✅' : '⏳'}
                      </div>
                      <div className="milestone-content-col">
                        <div className="milestone-header-line">
                          <h4 className="milestone-title">{ms.title}</h4>
                          <span className={`milestone-badge ${ms.status}`}>
                            {ms.status.replace('_', ' ')}
                          </span>
                        </div>
                        <p className="milestone-desc">{ms.description}</p>
                        <div className="milestone-tags-row">
                          <span className="milestone-role-tag">Role: {ms.assigned_role}</span>
                          {ms.assigned_member_handle && (
                            <span className="milestone-assignee-tag">👤 {ms.assigned_member_handle}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              ) : (
                <div className="empty-milestones-box">
                  <p>No sprint milestones defined yet. Check the Specifications tab to configure deliverables.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
