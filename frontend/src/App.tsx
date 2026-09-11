import React, { useState, useEffect, useCallback } from 'react'
import { useConversation } from './hooks/useConversation'
import { useReducedMotion } from './hooks/useReducedMotion'
import { TopHeader, type CognitiveMode } from './components/TopHeader/TopHeader'
import { MainWorkspace } from './components/MainWorkspace/MainWorkspace'
import { RightSidebar } from './components/RightSidebar/RightSidebar'
import { MoreMenu } from './components/MoreMenu/MoreMenu'
import { AtmosphericBackground } from './components/AtmosphericBackground/AtmosphericBackground'
import { LandingPage } from './components/LandingPage/LandingPage'
import { Sidebar } from './components/Sidebar/Sidebar'
import { GlowCursor } from './components/GlowCursor'
import { NotificationsDrawer, type SystemNotification } from './components/NotificationsDrawer/NotificationsDrawer'
import { PluginManagerModal } from './components/PluginManagerModal/PluginManagerModal'
import { KnowledgeVaultModal } from './components/KnowledgeVaultModal/KnowledgeVaultModal'
import { ConnectedAppsModal } from './components/ConnectedAppsModal/ConnectedAppsModal'
import { AuthDashboardModal } from './components/AuthDashboardModal/AuthDashboardModal'
import { NewProjectModal } from './components/NewProjectModal/NewProjectModal'
import { ProjectWorkspaceModal } from './components/ProjectWorkspaceModal/ProjectWorkspaceModal'
import { SelfImprovementHubModal } from './components/SelfImprovementHubModal/SelfImprovementHubModal'
import type { UserProfile } from './types/auth'
import type { Project, ProjectCreatePayload } from './types/project'
import type { SelfImprovementReport } from './types/improvement'
import { XEREN_SPECTER_THEMES } from './components/SpecterOrb/specterOrb.presets'
import './App.css'

export interface AppProps {
  initialView?: 'landing' | 'workspace'
  initialTransportType?: 'mock' | 'websocket'
}

export const App: React.FC<AppProps> = ({ initialView, initialTransportType }) => {
  const [currentView, setCurrentView] = useState<'landing' | 'workspace'>(() => {
    if (initialView) return initialView
    if (typeof window !== 'undefined') {
      if (window.location.hash === '#landing') return 'landing'
      if (window.location.hash === '#workspace') return 'workspace'
    }
    return 'workspace'
  })

  const { prefersReducedMotion, setReducedMotionOverride } = useReducedMotion()
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => typeof window !== 'undefined' ? window.innerWidth > 900 : true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false)

  // Interactive Modals and Navigation State
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
  const [isPluginsModalOpen, setIsPluginsModalOpen] = useState(false)
  const [isKnowledgeModalOpen, setIsKnowledgeModalOpen] = useState(false)
  const [isAppsModalOpen, setIsAppsModalOpen] = useState(false)
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [isProjectWorkspaceOpen, setIsProjectWorkspaceOpen] = useState(false)
  const [workspaceInitialTab, setWorkspaceInitialTab] = useState<'coach' | 'relay' | 'specs' | 'roles' | 'milestones'>('coach')
  const [isImprovementHubOpen, setIsImprovementHubOpen] = useState(false)
  const [improvementReport, setImprovementReport] = useState<SelfImprovementReport | null>(null)
  const [activeProject, setActiveProject] = useState<Project | null>({
    project_id: 'proj_cyberforge_group',
    name: 'CyberForge AI Engine',
    description: 'Collaborative team project for multi-model autonomous agent development and distributed deployment.',
    project_type: 'group',
    owner_id: 'usr_dev_01',
    owner_name: 'Alex Mercer',
    owner_handle: '@xeren_dev',
    created_at: '2026-09-07T12:00:00Z',
    updated_at: '2026-09-07T12:00:00Z',
    members: [
      {
        user_id: 'usr_dev_01',
        handle: '@xeren_dev',
        display_name: 'Alex Mercer',
        email: 'alex.mercer@xeren.ai',
        role: 'architect',
        joined_at: '2026-09-07T12:00:00Z',
        is_owner: true,
        active_task: 'Designing zero-interruption workstation pipelines',
      },
      {
        user_id: 'usr_peer_02',
        handle: '@sarah_ai',
        display_name: 'Dr. Sarah Chen',
        email: 'sarah.chen@deepmind-labs.org',
        role: 'ai_specialist',
        joined_at: '2026-09-07T12:00:00Z',
        avatar_url: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&q=80',
        is_owner: false,
        active_task: 'Fine-tuning prompt reasoning templates',
      },
    ],
    invites: [],
    specifications: {
      tech_stack: ['TypeScript', 'FastAPI', 'MongoDB Atlas', 'React 19', 'WebSockets'],
      architecture_pattern: 'Distributed Multi-Agent Event Bus',
      constraints: [
        'Zero-interruption workstation isolation',
        'Strict role-based action gating',
        'Real-time sync latency < 50ms',
      ],
      target_apis: ['OpenAI API', 'Anthropic Claude API', 'Gemini Pro API', 'MongoDB Atlas'],
      deliverables: [
        'Parallel collaborative workstations',
        'AI Coach integration',
        'Role matrix management',
      ],
    },
    milestones: [
      {
        milestone_id: 'ms_grp_01',
        title: 'Real-time Workstation Event Bus',
        description: 'Deploy WebSocket multiplexer for zero-lag peer collaboration',
        assigned_role: 'architect',
        assigned_member_handle: '@xeren_dev',
        status: 'completed',
      },
      {
        milestone_id: 'ms_grp_02',
        title: 'Multi-Model Reasoning Benchmarks',
        description: 'Benchmark Claude 3.5 Sonnet vs Gemini 2.0 Flash for sub-agents',
        assigned_role: 'ai_specialist',
        assigned_member_handle: '@sarah_ai',
        status: 'in_progress',
      },
      {
        milestone_id: 'ms_grp_03',
        title: 'RBAC Security Gate Auditing',
        description: 'Enforce role permissions between Architect, Engineer, and Reviewer',
        assigned_role: 'engineer',
        assigned_member_handle: '@xeren_dev',
        status: 'pending',
      },
    ],
    tags: ['team', 'collaboration', 'neural', 'sync'],
    synced_with_mongo: true,
  })
  const [activeMode, setActiveMode] = useState<CognitiveMode>('think')
  const [activeCommandCenterTab, setActiveCommandCenterTab] = useState<'freelance' | 'security' | 'research' | 'channels'>('freelance')

  // System Version & MongoDB status
  const [dbConnected, setDbConnected] = useState(true)
  const [dbMode, setDbMode] = useState('atlas')
  const [systemVersion, setSystemVersion] = useState('v1.2.0')

  // User Profile
  const [currentUser, setCurrentUser] = useState<UserProfile>({
    user_id: 'usr_lead_01',
    handle: '@xeren_dev',
    display_name: 'Xeren Autonomous Lead',
    email: 'developer@xeren.ai',
    phone_number: '+1 (555) 019-2834',
    avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80',
    plan_tier: 'Pro Studio',
    linked_methods: ['google', 'github', 'passkey'],
    passkeys: [
      {
        credential_id: 'cred_fido2_winhello_01',
        device_name: 'Windows Hello / Touch ID Key',
        public_key: 'p256_mock_key',
        created_at: '2026-09-07T12:00:00Z',
        last_used_at: '2026-09-07T12:00:00Z',
      },
    ],
    active_project_id: 'proj_xeren_core',
    created_at: '2026-09-07T12:00:00Z',
    last_login_at: '2026-09-07T12:00:00Z',
  })

  // Real System Notifications (including project invites)
  const [notifications, setNotifications] = useState<SystemNotification[]>([
    {
      id: 'notif-invite-1',
      timestamp: '5m ago',
      title: 'Project Invitation: CyberForge AI Engine',
      message: '@sarah_ai invited you to join the collaborative group project as Editor.',
      type: 'project_invite',
      read: false,
      inviteId: 'inv_cyberforge_01',
      projectId: 'proj_cyberforge_group',
      projectName: 'CyberForge AI Engine',
      inviterHandle: '@sarah_ai',
      role: 'editor',
    },
    {
      id: 'notif-1',
      timestamp: 'Just now',
      title: 'Security Gate Active',
      message: 'AES-256-GCM hardware crypto initialized. 3-Tier isolation active.',
      type: 'security',
      read: false,
    },
    {
      id: 'notif-2',
      timestamp: '2m ago',
      title: 'Freelance Workspace Initialized',
      message: 'Fiverr & Upwork automated listener is monitoring order events in parallel.',
      type: 'order',
      read: false,
    },
    {
      id: 'notif-3',
      timestamp: '15m ago',
      title: 'Strawberry AI Ready',
      message: '4-angle query planner and domain authority verification matrix loaded.',
      type: 'research',
      read: true,
    },
  ])

  // Fetch initial system version & user profile from backend
  useEffect(() => {
    const fetchSystemMeta = async () => {
      try {
        const verResp = await fetch('/api/system/version')
        if (verResp.ok) {
          const verData = await verResp.json()
          if (verData.backend_version) setSystemVersion(`v${verData.backend_version}`)
          if (verData.database) {
            setDbConnected(verData.database.connected ?? true)
            setDbMode(verData.database.mode ?? 'atlas')
          }
        }
      } catch (_) {
        // Run gracefully with local fallback
      }

      try {
        const userResp = await fetch('/api/auth/me')
        if (userResp.ok) {
          const uData = await userResp.json()
          if (uData.user) setCurrentUser(uData.user)
        }
      } catch (_) {
        // Local fallback
      }

      try {
        const impResp = await fetch('/api/llm/improvements/status')
        if (impResp.ok) {
          const impData = await impResp.json()
          setImprovementReport(impData)
        }
      } catch (_) {
        // Local fallback
      }
    }

    fetchSystemMeta()
  }, [])

  // Project Creation Handler
  const handleCreateProject = async (payload: ProjectCreatePayload): Promise<Project> => {
    try {
      const resp = await fetch('/api/projects/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (resp.ok) {
        const data = await resp.json()
        const created: Project = data.project
        // Add activity notification
        setNotifications((prev) => [
          {
            id: `notif-created-${Date.now()}`,
            timestamp: 'Just now',
            title: `Workspace Initialized: ${created.name}`,
            message:
              created.project_type === 'solo'
                ? 'Private isolated solo workspace created with local hardware vault.'
                : `Collaborative group workspace live with ${created.members.length} members and ${created.invites.length} queued invites.`,
            type: 'system',
            read: false,
          },
          ...prev,
        ])
        return created
      }
    } catch (_) {
      // Offline mock fallback
    }

    const fallbackProj: Project = {
      project_id: `proj_${Date.now()}`,
      name: payload.name,
      description: payload.description,
      project_type: payload.project_type,
      owner_id: currentUser.user_id,
      owner_name: currentUser.display_name,
      owner_handle: currentUser.handle,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      members: [
        {
          user_id: currentUser.user_id,
          handle: currentUser.handle,
          display_name: currentUser.display_name,
          email: currentUser.email,
          role: 'owner',
          joined_at: new Date().toISOString(),
          is_owner: true,
        },
      ],
      invites: (payload.initial_invites || []).map((inv, idx) => ({
        invite_id: `inv_${idx}_${Date.now()}`,
        project_id: `proj_${Date.now()}`,
        project_name: payload.name,
        invite_type: inv.invite_type,
        recipient: inv.target,
        role: inv.role,
        token: `xrn_join_${Math.random()}`,
        verification_code: `${Math.floor(100000 + Math.random() * 900000)}`,
        status: 'pending',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
        sender_id: currentUser.user_id,
        sender_name: currentUser.display_name,
        sender_handle: currentUser.handle,
      })),
      tags: payload.tags || [],
      synced_with_mongo: dbConnected,
    }

    setNotifications((prev) => [
      {
        id: `notif-created-${Date.now()}`,
        timestamp: 'Just now',
        title: `Workspace Initialized: ${fallbackProj.name}`,
        message:
          fallbackProj.project_type === 'solo'
            ? 'Solo workstation ready with isolated local vault.'
            : `Group workspace ready with ${fallbackProj.invites.length} member invitations dispatched.`,
        type: 'system',
        read: false,
      },
      ...prev,
    ])

    return fallbackProj
  }

  // Invite Acceptance Handler
  const handleAcceptInvite = async (inviteId: string) => {
    try {
      await fetch(`/api/projects/invites/${inviteId}/accept`, { method: 'POST' })
    } catch (_) {
      // Local fallback
    }

    setNotifications((prev) =>
      prev.map((n) =>
        n.inviteId === inviteId || n.id === inviteId
          ? {
              ...n,
              read: true,
              message: 'You accepted the invitation and joined the project workspace!',
            }
          : n
      )
    )

    setNotifications((prev) => [
      {
        id: `notif-join-${Date.now()}`,
        timestamp: 'Just now',
        title: 'Project Workspace Joined',
        message: 'You are now an active collaborator. Shared sessions and tools are synchronized.',
        type: 'project_invite',
        read: false,
      },
      ...prev,
    ])
  }

  // Invite Decline Handler
  const handleDeclineInvite = async (inviteId: string) => {
    try {
      await fetch(`/api/projects/invites/${inviteId}/decline`, { method: 'POST' })
    } catch (_) {
      // Local fallback
    }
    setNotifications((prev) => prev.filter((n) => n.inviteId !== inviteId && n.id !== inviteId))
  }

  // Social Login Handler (Google, GitHub, Facebook)
  const handleSocialLogin = async (provider: 'google' | 'github' | 'facebook') => {
    try {
      const resp = await fetch('/api/auth/social', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      })
      if (resp.ok) {
        const data = await resp.json()
        if (data.user) {
          setCurrentUser(data.user)
          return
        }
      }
    } catch (_) {
      // Local fallback
    }

    // Local fallback update
    setCurrentUser((prev) => ({
      ...prev,
      linked_methods: Array.from(new Set([...prev.linked_methods, provider])),
    }))
  }

  // Passkey Handlers
  const handlePasskeyAuth = async () => {
    const credId = currentUser.passkeys[0]?.credential_id || 'cred_fido2_winhello_01'
    try {
      await fetch('/api/auth/passkey/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential_id: credId }),
      })
    } catch (_) {
      // Local fallback
    }
  }

  const handleRegisterPasskey = async (deviceName: string) => {
    const newCredId = `cred_passkey_${Date.now()}`
    try {
      const resp = await fetch('/api/auth/passkey/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_name: deviceName,
          credential_id: newCredId,
          public_key: 'p256_mock_key',
        }),
      })
      if (resp.ok) {
        const data = await resp.json()
        if (data.user) {
          setCurrentUser(data.user)
          return
        }
      }
    } catch (_) {
      // Local fallback
    }

    setCurrentUser((prev) => ({
      ...prev,
      linked_methods: Array.from(new Set([...prev.linked_methods, 'passkey'])),
      passkeys: [
        ...prev.passkeys,
        {
          credential_id: newCredId,
          device_name: deviceName,
          public_key: 'p256_mock_key',
          created_at: new Date().toISOString(),
          last_used_at: new Date().toISOString(),
        },
      ],
    }))
  }

  // OTP Handlers
  const handleSendOtp = async (target: string, method: 'email' | 'phone'): Promise<string | undefined> => {
    try {
      const resp = await fetch('/api/auth/otp/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, method }),
      })
      if (resp.ok) {
        const data = await resp.json()
        return data.code_preview
      }
    } catch (_) {
      // Local fallback preview code
    }
    return '489201'
  }

  const handleVerifyOtp = async (target: string, code: string, method: 'email' | 'phone'): Promise<boolean> => {
    try {
      const resp = await fetch('/api/auth/otp/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, code, method }),
      })
      if (resp.ok) {
        const data = await resp.json()
        if (data.user) setCurrentUser(data.user)
        return true
      }
    } catch (_) {
      // Local fallback
    }

    // Local fallback update
    setCurrentUser((prev) => ({
      ...prev,
      email: method === 'email' ? target : prev.email,
      phone_number: method === 'phone' ? target : prev.phone_number,
      linked_methods: Array.from(new Set([...prev.linked_methods, method === 'email' ? 'email_otp' : 'phone_otp'])),
    }))
    return true
  }

  const defaultTransport =
    typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test'
      ? 'mock'
      : 'websocket'

  const {
    presenceState,
    messages,
    currentStreamingText,
    currentStreamingId,
    agentProgress,
    activeMilestone,
    activeAmplitude,
    isListening,
    isSpeaking,
    isVoiceOutputEnabled,
    setIsVoiceOutputEnabled,
    connectionState,
    transportType,
    switchTransport,
    reconnect,
    voiceInputError,
    startListening,
    stopListening,
    sendMessage,
    proceedWithStagedPlan,
    interrupt,
    clearHistory,
  } = useConversation({ initialTransportType: initialTransportType || defaultTransport })

  // Global Keyboard Shortcuts
  const handleGlobalKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName?.toLowerCase()
      const isInputActive = activeTag === 'input' || activeTag === 'textarea'

      // Barge-in shortcut: Escape key
      if (e.key === 'Escape') {
        if (isListening || presenceState === 'listening') {
          e.preventDefault()
          stopListening()
        } else if (
          presenceState === 'speaking' ||
          presenceState === 'acting' ||
          presenceState === 'thinking' ||
          isSpeaking ||
          currentStreamingId
        ) {
          e.preventDefault()
          interrupt()
        }
        return
      }

      // Voice shortcut: Space or 'm' (only if not inside text input)
      if (!isInputActive && (e.code === 'Space' || e.key.toLowerCase() === 'm')) {
        e.preventDefault()
        if (isListening) {
          stopListening()
        } else {
          startListening()
        }
      }
    },
    [presenceState, isSpeaking, currentStreamingId, interrupt, isListening, stopListening, startListening]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [handleGlobalKeyDown])

  const currentTheme = XEREN_SPECTER_THEMES[presenceState] || XEREN_SPECTER_THEMES.idle
  const cursorColor = currentView === 'landing' ? '#10b981' : currentTheme.colorA
  const cursorSecondaryColor = currentView === 'landing' ? '#047857' : currentTheme.colorB

  const mainView =
    currentView === 'landing' ? (
      <LandingPage
        onEnterWorkspace={() => {
          setCurrentView('workspace')
          if (typeof window !== 'undefined') {
            window.location.hash = '#workspace'
          }
        }}
      />
    ) : (
      <div className={`app-shell app-container ${prefersReducedMotion ? 'reduced-motion' : ''}`}>
        {/* Cinematic Computational Atmospheric Background */}
        <AtmosphericBackground
          state={presenceState}
          isReducedMotion={prefersReducedMotion}
        />

        {/* 1. TOP HEADER */}
        <TopHeader
          connectionState={connectionState}
          transportType={transportType}
          activeMode={activeMode}
          onSelectMode={setActiveMode}
          unreadNotificationsCount={notifications.filter((n) => !n.read).length}
          onOpenNotifications={() => setIsNotificationsOpen(true)}
          onOpenPlugins={() => setIsPluginsModalOpen(true)}
          onOpenKnowledge={() => setIsKnowledgeModalOpen(true)}
          onOpenConnectedApps={() => setIsAppsModalOpen(true)}
          onOpenNewProject={() => setIsNewProjectModalOpen(true)}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          activeProjectName={activeProject?.name}
          onOpenProjectWorkspace={() => setIsProjectWorkspaceOpen(true)}
          currentUserHandle={currentUser.handle}
          currentUserAvatar={currentUser.avatar_url}
          dbConnected={dbConnected}
          dbMode={dbMode}
          systemVersion={systemVersion}
          adaptiveScore={improvementReport?.adaptive_score ?? 94.8}
          onOpenImprovementHub={() => setIsImprovementHubOpen(true)}
          onGoHome={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          onReconnect={reconnect}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          onToggleRightPanel={() => setIsRightPanelOpen((prev) => !prev)}
          onViewLanding={() => {
            setCurrentView('landing')
            if (typeof window !== 'undefined') {
              window.location.hash = '#landing'
            }
          }}
        />

        {/* ULTRA-CLEAN WORKSPACE LAYOUT */}
        <div className="app-body-layout">
          {/* Mobile overlay backdrop */}
          <div
            className={`mobile-overlay ${(isRightPanelOpen || isSidebarOpen) ? 'active' : ''}`}
            onClick={() => {
              setIsRightPanelOpen(false)
              setIsSidebarOpen(false)
            }}
            aria-hidden="true"
          />

          {/* LEFT SIDEBAR (Ultra-Clean Workspace Navigation) */}
          <Sidebar
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
            onToggle={() => setIsSidebarOpen((prev) => !prev)}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onNewChat={clearHistory}
            onOpenNewProject={() => setIsNewProjectModalOpen(true)}
            onOpenPlugins={() => setIsPluginsModalOpen(true)}
            onOpenApps={() => setIsAppsModalOpen(true)}
            onOpenKnowledge={() => setIsKnowledgeModalOpen(true)}
            onOpenProjects={() => {
              setWorkspaceInitialTab('coach')
              setIsProjectWorkspaceOpen(true)
            }}
            onOpenRelay={() => {
              setWorkspaceInitialTab('relay')
              setIsProjectWorkspaceOpen(true)
            }}
            activeProjectName={activeProject?.name}
            currentUserHandle={currentUser.handle}
            onSelectNav={(navId) => {
              if (navId === 'projects') {
                setWorkspaceInitialTab('coach')
                setIsProjectWorkspaceOpen(true)
              } else if (navId === 'relay') {
                setWorkspaceInitialTab('relay')
                setIsProjectWorkspaceOpen(true)
              } else if (navId === 'new-project') setIsNewProjectModalOpen(true)
              else if (navId === 'plugins') setIsPluginsModalOpen(true)
              else if (navId === 'web-agent' || navId === 'apps') setIsAppsModalOpen(true)
              else if (navId === 'knowledge') setIsKnowledgeModalOpen(true)
              else if (navId === 'new-chat') clearHistory()
              else if (navId === 'settings') setIsSettingsOpen(true)
            }}
          />

          {/* CENTRAL MAIN WORKSPACE (Full Width Studio Canvas) */}
          <MainWorkspace
            presenceState={presenceState}
            activeAmplitude={activeAmplitude}
            prefersReducedMotion={prefersReducedMotion}
            messages={messages}
            currentStreamingText={currentStreamingText}
            currentStreamingId={currentStreamingId}
            agentProgress={agentProgress}
            activeMilestone={activeMilestone}
            isListening={isListening}
            isSpeaking={isSpeaking}
            voiceError={voiceInputError}
            activeMode={activeMode}
            onSelectMode={setActiveMode}
            activeCommandCenterTab={activeCommandCenterTab}
            onCommandCenterTabChange={setActiveCommandCenterTab}
            onSendMessage={(text) => sendMessage(text, 'text')}
            onProceedPlan={proceedWithStagedPlan}
            onStartListening={startListening}
            onStopListening={stopListening}
            onInterrupt={interrupt}
            isVoiceOutputEnabled={isVoiceOutputEnabled}
            onToggleVoiceOutput={setIsVoiceOutputEnabled}
          />

          {/* 4. FLOATING COMMAND HUB (Bottom-Right Action Trigger + Chart of Subsystem Buttons) */}
          <RightSidebar
            isOpen={isRightPanelOpen}
            onToggle={() => setIsRightPanelOpen((prev) => !prev)}
            transportType={transportType}
            connectionState={connectionState}
            onSelectPrompt={(prompt) => sendMessage(prompt, 'text')}
            onOpenPlugins={() => setIsPluginsModalOpen(true)}
            onOpenKnowledge={() => setIsKnowledgeModalOpen(true)}
            onOpenConnectedApps={() => setIsAppsModalOpen(true)}
            onOpenImprovementHub={() => setIsImprovementHubOpen(true)}
            onOpenWorkspaces={(tab) => {
              if (tab) setActiveCommandCenterTab(tab)
              document.querySelector('.command-center-container')?.scrollIntoView({ behavior: 'smooth' })
            }}
            onClose={() => setIsRightPanelOpen(false)}
          />
        </div>

        {/* Activity & Notifications Drawer */}
        <NotificationsDrawer
          isOpen={isNotificationsOpen}
          onClose={() => setIsNotificationsOpen(false)}
          notifications={notifications}
          onClearAll={() => setNotifications([])}
          onMarkAllRead={() =>
            setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
          }
          onDismiss={(id) =>
            setNotifications((prev) => prev.filter((n) => n.id !== id))
          }
          onAcceptInvite={handleAcceptInvite}
          onDeclineInvite={handleDeclineInvite}
        />

        {/* Dual-Mode New Project Modal (Solo vs Group Workspaces & Member Invites) */}
        <NewProjectModal
          isOpen={isNewProjectModalOpen}
          onClose={() => setIsNewProjectModalOpen(false)}
          currentUser={currentUser}
          onCreateProject={handleCreateProject}
        />

        {/* Dedicated Collaborative Project Workspace & AI Coach */}
        <ProjectWorkspaceModal
          isOpen={isProjectWorkspaceOpen}
          onClose={() => setIsProjectWorkspaceOpen(false)}
          project={activeProject}
          currentUserId={currentUser.user_id}
          initialTab={workspaceInitialTab}
          onProjectUpdated={(updated) => setActiveProject(updated)}
        />

        {/* Multi-Method Authentication & User Profile Dashboard */}
        <AuthDashboardModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
          currentUser={currentUser}
          onUpdateProfile={(updated) => setCurrentUser((prev) => ({ ...prev, ...updated }))}
          onSocialLogin={handleSocialLogin}
          onPasskeyAuth={handlePasskeyAuth}
          onRegisterPasskey={handleRegisterPasskey}
          onSendOtp={handleSendOtp}
          onVerifyOtp={handleVerifyOtp}
        />

        {/* Extensible Autonomous Plugin Registry Modal */}
        <PluginManagerModal
          isOpen={isPluginsModalOpen}
          onClose={() => setIsPluginsModalOpen(false)}
        />

        {/* Local Qdrant Knowledge Vault & RAG Modal */}
        <KnowledgeVaultModal
          isOpen={isKnowledgeModalOpen}
          onClose={() => setIsKnowledgeModalOpen(false)}
        />

        {/* Model Context Protocol (MCP) & Connected Apps Hub Modal */}
        <ConnectedAppsModal
          isOpen={isAppsModalOpen}
          onClose={() => setIsAppsModalOpen(false)}
        />

        {/* Neural Learning & LLM Self-Improvement Hub Modal */}
        <SelfImprovementHubModal
          isOpen={isImprovementHubOpen}
          onClose={() => setIsImprovementHubOpen(false)}
          report={improvementReport}
          onRefreshReport={async () => {
            try {
              const res = await fetch('/api/llm/improvements/status')
              if (res.ok) {
                const data = await res.json()
                setImprovementReport(data)
              }
            } catch (_) {}
          }}
        />

        {/* Settings Modal / Menu */}
        <MoreMenu
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          transportType={transportType}
          onSwitchTransport={switchTransport}
          isVoiceOutputEnabled={isVoiceOutputEnabled}
          onToggleVoiceOutput={setIsVoiceOutputEnabled}
          isReducedMotion={prefersReducedMotion}
          onToggleReducedMotion={(val) => setReducedMotionOverride(val)}
          onClearHistory={clearHistory}
        />
      </div>
    )

  return (
    <GlowCursor
      color={cursorColor}
      secondaryColor={cursorSecondaryColor}
      trailLength={36}
      trailWidth={6}
      trailTaper={0.8}
      followSpeed={0.26}
      glowIntensity={2.2}
      glowSpread={1.2}
      hotspot={0.68}
      brightness={1.25}
      opacity={0.95}
      pulseSpeed={1.2}
      noiseStrength={0.04}
      idleFade
      idleTimeout={750}
      fadeDuration={900}
      blendMode="screen"
      className="global-glow-cursor-app"
      data-testid="global-glow-cursor"
    >
      {mainView}
    </GlowCursor>
  )
}

export default App
