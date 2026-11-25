import React, { useState, useEffect } from 'react'
import './XerenRelay.css'

export interface ConnectedApp {
  id: string
  name: string
  icon: string
  description: string
  category: 'vcs' | 'ai_model' | 'design' | 'runtime'
  status: 'connected' | 'disconnected' | 'authenticating'
  permissions: string[]
  activeAccount: string
  lastSync: string
}

export interface RelayTask {
  id: string
  title: string
  appTarget: 'github' | 'chatgpt' | 'figma' | 'runtime'
  status: 'in_progress' | 'completed' | 'queued'
  progressPercent: number
  statusText: string
  timestamp: string
  report?: {
    duration: string
    filesTouched?: string[]
    testsPassed?: string
    outputSummary: string
    securityAudit: string
    artifactUrl?: string
  }
}

export interface XerenRelayProps {
  projectId?: string
  projectName?: string
}

export const XerenRelay: React.FC<XerenRelayProps> = ({
  projectId = 'proj_cyberforge_group',
  projectName = 'CyberForge AI Engine',
}) => {
  // Filter tabs for tasks
  const [taskFilter, setTaskFilter] = useState<'all' | 'in_progress' | 'completed' | 'queued'>('all')
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>('TASK-RELAY-1049')
  const [activeAlert, setActiveAlert] = useState<string | null>(null)

  // 1. GITHUB FILE PUSH REAL-TIME STATE
  const [githubPushState, setGithubPushState] = useState({
    isPushing: false,
    filesUploaded: 18,
    totalFiles: 24,
    currentFile: 'src/components/XerenRelay/XerenRelay.tsx',
    transferSpeed: '2.4 MB/s',
    branch: 'main',
    commitSha: '7f4a21e',
    statusMessage: 'Streaming file pack to origin/main...',
  })

  // 2. CHATGPT / DALL-E GENERATION STATE
  const [imageGenState, setImageGenState] = useState({
    isGenerating: false,
    progress: 88,
    stepDescription: 'Diffusion step 44/50 · High-res latent upscaling & denoising',
    prompt: 'Futuristic Obsidian Orb with emerald bioluminescent circuitry in 3D dark glass',
    completedAssetUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80',
    lastCompletedAt: null as string | null,
  })

  // 3. RATE LIMIT & COOLDOWN MONITOR (e.g. Resets at 10:00 AM)
  const [rateLimitState, setRateLimitState] = useState({
    modelName: 'OpenAI GPT-4o & DALL-E 3',
    hourlyUsed: 48,
    hourlyLimit: 50,
    isCooldownActive: true,
    resetTimeLabel: '10:00 AM',
    remainingSeconds: 1342, // ~22m 22s
  })

  // Connected Apps state
  const [apps, setApps] = useState<ConnectedApp[]>([
    {
      id: 'app_github',
      name: 'GitHub Enterprise',
      icon: '🐙',
      description: 'Repository synchronization, automated push, branch gating, and PR dispatch',
      category: 'vcs',
      status: 'connected',
      permissions: ['repo:write', 'workflow:run', 'commit:push', 'status:check'],
      activeAccount: 'xeren-dev (@xeren_dev)',
      lastSync: '12 seconds ago',
    },
    {
      id: 'app_chatgpt',
      name: 'ChatGPT / DALL-E 3',
      icon: '✨',
      description: 'Multi-modal reasoning, generative asset rendering, and high-fidelity text synthesis',
      category: 'ai_model',
      status: 'connected',
      permissions: ['model:generate', 'images:create', 'embeddings:read'],
      activeAccount: 'org_deepmind_tier4',
      lastSync: 'Just now',
    },
    {
      id: 'app_figma',
      name: 'Figma Tokens API',
      icon: '🎨',
      description: 'Live vector component inspection, design tokens, and CSS layout mapping',
      category: 'design',
      status: 'connected',
      permissions: ['file:read', 'components:sync'],
      activeAccount: 'team_cyberforge_design',
      lastSync: '4 minutes ago',
    },
    {
      id: 'app_runtime',
      name: 'Sandboxed Cloud Runtime',
      icon: '⚡',
      description: 'Isolated container runtime with zero-network unauthorized egress verification',
      category: 'runtime',
      status: 'connected',
      permissions: ['bash:exec', 'fs:readwrite', 'sandbox:isolated'],
      activeAccount: 'node_us_east_relay_09',
      lastSync: 'Live (12ms ping)',
    },
  ])

  // Tasks list with comprehensive work reports
  const [tasks, setTasks] = useState<RelayTask[]>([
    {
      id: 'TASK-RELAY-1049',
      title: 'Synchronize multi-module codebase & assets to origin/main',
      appTarget: 'github',
      status: 'in_progress',
      progressPercent: 75,
      statusText: '18 of 24 files uploaded (75%) · Transfer speed: 2.4 MB/s',
      timestamp: 'Started 1m ago',
      report: {
        duration: '1m 24s elapsed',
        filesTouched: [
          'src/components/XerenRelay/XerenRelay.tsx',
          'src/components/XerenRelay/XerenRelay.css',
          'src/components/ProjectWorkspaceModal/ProjectWorkspaceModal.tsx',
          'src/tests/xeren_relay.test.tsx',
        ],
        testsPassed: 'All pre-push git hooks verified clean',
        outputSummary: 'Uploading delta packs for 24 modified assets. Zero commit conflicts encountered.',
        securityAudit: 'GPG signature verified · Zero secret leaks detected in git diff',
      },
    },
    {
      id: 'TASK-RELAY-1048',
      title: 'Render Obsidian 3D Mascot Orb Concept via ChatGPT / DALL-E',
      appTarget: 'chatgpt',
      status: 'completed',
      progressPercent: 100,
      statusText: 'Generation finished · Notification dispatched to user',
      timestamp: 'Completed 3m ago',
      report: {
        duration: '52 seconds',
        filesTouched: ['public/assets/mascot_obsidian_core.webp'],
        testsPassed: 'Resolution: 2048x2048 · WebP compressed (384KB)',
        outputSummary: 'Completed prompt: Obsidian Orb with emerald bioluminescent rim light and 3D eye tracking.',
        securityAudit: 'Prompt checked against content safety filters · 100% compliant',
        artifactUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80',
      },
    },
    {
      id: 'TASK-RELAY-1047',
      title: 'Continuous Autonomous Sandbox Unit & Regression Verification',
      appTarget: 'runtime',
      status: 'completed',
      progressPercent: 100,
      statusText: 'All test assertions passed (18/18 test suites)',
      timestamp: 'Completed 12m ago',
      report: {
        duration: '3m 15s',
        filesTouched: ['tests/benchmarks.log', 'coverage/lcov.info'],
        testsPassed: '18 / 18 suites passed · 98.4% code coverage',
        outputSummary: 'Evaluated zero-interruption workstation isolation, state multiplexing, and WebSocket transport.',
        securityAudit: 'Sandboxed container verified · Zero egress violations recorded',
      },
    },
    {
      id: 'TASK-RELAY-1050',
      title: 'Figma Vector Tokens Extraction & Dark Theme Component Sync',
      appTarget: 'figma',
      status: 'queued',
      progressPercent: 0,
      statusText: 'Queued · Awaiting model rate limit window reset at 10:00 AM',
      timestamp: 'Queued 6m ago',
      report: {
        duration: 'Pending execution',
        outputSummary: 'Scheduled to pull updated typography, hex tokens, and icon frames once upstream quota cooldown ends.',
        securityAudit: 'OAuth2 token valid · Scopes authorized',
      },
    },
  ])

  // New task input state
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskTarget, setNewTaskTarget] = useState<'github' | 'chatgpt' | 'figma' | 'runtime'>('github')

  // Live countdown timer for rate limits
  useEffect(() => {
    const timer = setInterval(() => {
      setRateLimitState((prev) => ({
        ...prev,
        remainingSeconds: prev.remainingSeconds > 0 ? prev.remainingSeconds - 1 : 1800,
      }))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m}m ${s < 10 ? '0' : ''}${s}s`
  }

  // SIMULATE LIVE GITHUB PUSH
  const handleSimulateGitPush = () => {
    setGithubPushState((prev) => ({
      ...prev,
      isPushing: true,
      filesUploaded: 1,
      statusMessage: 'Preparing git pack index...',
    }))

    setActiveAlert('⚡ GitHub Push initiated: Tracking real-time file upload stream...')

    let current = 1
    const total = 24
    const interval = setInterval(() => {
      current += 3
      if (current >= total) {
        current = total
        clearInterval(interval)
        setGithubPushState((prev) => ({
          ...prev,
          isPushing: false,
          filesUploaded: total,
          statusMessage: `Successfully pushed 24/24 files to origin/main (Commit: ${prev.commitSha})`,
        }))

        // Update task
        setTasks((prev) =>
          prev.map((t) =>
            t.id === 'TASK-RELAY-1049'
              ? {
                  ...t,
                  status: 'completed',
                  progressPercent: 100,
                  statusText: '24 of 24 files uploaded (100%) · Push completed',
                  report: {
                    ...t.report!,
                    outputSummary: 'All 24 files synced to origin/main. Git SHA verified: 7f4a21e.',
                  },
                }
              : t
          )
        )

        setActiveAlert('✅ GitHub Push Completed: All 24 files uploaded and verified on remote!')
      } else {
        const fileNames = [
          'src/components/XerenRelay/XerenRelay.tsx',
          'src/components/XerenRelay/XerenRelay.css',
          'src/types/project.ts',
          'src/App.tsx',
          'src/tests/xeren_relay.test.tsx',
          'public/assets/mascot.webp',
        ]
        const currentFile = fileNames[Math.floor(Math.random() * fileNames.length)]

        setGithubPushState((prev) => ({
          ...prev,
          filesUploaded: current,
          currentFile,
          statusMessage: `Uploading file ${current}/${total} (${Math.round((current / total) * 100)}%) · ${currentFile}`,
        }))

        setTasks((prev) =>
          prev.map((t) =>
            t.id === 'TASK-RELAY-1049'
              ? {
                  ...t,
                  progressPercent: Math.round((current / total) * 100),
                  statusText: `${current} of ${total} files uploaded (${Math.round((current / total) * 100)}%) · Transfer speed: 2.8 MB/s`,
                }
              : t
          )
        )
      }
    }, 450)
  }

  // SIMULATE CHATGPT / DALL-E GENERATION & TRIGGER NOTIFICATION
  const handleSimulateImageGen = () => {
    setImageGenState((prev) => ({
      ...prev,
      isGenerating: true,
      progress: 10,
      stepDescription: 'Sending prompt embeddings to ChatGPT / DALL-E neural engine...',
    }))

    setActiveAlert('✨ Image generation started: Synthesizing 3D Obsidian Mascot Orb...')

    let progress = 10
    const steps = [
      'Initializing text-to-image latent space...',
      'Diffusion pass 1/4 · Outlining spherical topology and shadows...',
      'Diffusion pass 2/4 · Applying obsidian refractive shaders...',
      'Diffusion pass 3/4 · Illuminating emerald eye gradients & rim glow...',
      'Diffusion pass 4/4 · High-res 2048px upscaling and post-sharpening...',
    ]

    const interval = setInterval(() => {
      progress += 18
      if (progress >= 100) {
        clearInterval(interval)
        setImageGenState((prev) => ({
          ...prev,
          isGenerating: false,
          progress: 100,
          stepDescription: 'Asset completed and verified in Knowledge Vault',
          lastCompletedAt: new Date().toLocaleTimeString(),
        }))

        setActiveAlert(
          '🔔 Xeren Relay Alert: Image generation complete! "Obsidian Orb 3D Core" is ready to download.'
        )
      } else {
        const stepIdx = Math.min(Math.floor((progress / 100) * steps.length), steps.length - 1)
        setImageGenState((prev) => ({
          ...prev,
          progress,
          stepDescription: steps[stepIdx],
        }))
      }
    }, 400)
  }

  // TOGGLE PERMISSION SCOPE
  const handleToggleAppStatus = (appId: string) => {
    setApps((prev) =>
      prev.map((app) => {
        if (app.id === appId) {
          const nextStatus = app.status === 'connected' ? 'disconnected' : 'connected'
          return { ...app, status: nextStatus }
        }
        return app
      })
    )
  }

  // DISPATCH NEW TASK
  const handleDispatchTask = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTaskTitle.trim()) return

    const newTask: RelayTask = {
      id: `TASK-RELAY-${Math.floor(1051 + Math.random() * 8900)}`,
      title: newTaskTitle.trim(),
      appTarget: newTaskTarget,
      status: 'in_progress',
      progressPercent: 15,
      statusText: `Dispatched to ${newTaskTarget.toUpperCase()} relay · Initializing worker thread...`,
      timestamp: 'Just now',
      report: {
        duration: 'In execution',
        outputSummary: `Task initiated via autonomous Xeren Relay pipeline for ${projectName}.`,
        securityAudit: 'Zero-trust runtime guardrails applied',
      },
    }

    setTasks([newTask, ...tasks])
    setNewTaskTitle('')
    setActiveAlert(`🚀 Task assigned to Xeren Relay: "${newTask.title}"`)
  }

  const filteredTasks = tasks.filter((t) => {
    if (taskFilter === 'all') return true
    return t.status === taskFilter
  })

  const inProgressCount = tasks.filter((t) => t.status === 'in_progress').length
  const completedCount = tasks.filter((t) => t.status === 'completed').length
  const queuedCount = tasks.filter((t) => t.status === 'queued').length

  const githubPercent = Math.round((githubPushState.filesUploaded / githubPushState.totalFiles) * 100)

  return (
    <div className="xeren-relay-container" id="xeren-relay-view" data-testid="xeren-relay-container" data-project-id={projectId}>
      {/* 1. RELAY HERO HEADER & TOP STATS */}
      <header className="relay-header">
        <div className="relay-header-left">
          <div className="relay-badge-pill">
            <span className="relay-pulse-dot"></span>
            <span className="relay-badge-title">AUTONOMOUS BACKGROUND ENGINE</span>
          </div>
          <h2 className="relay-title">
            Xeren <span className="text-gradient">Relay</span>
          </h2>
          <p className="relay-subtitle">
            Autonomous background worker for <strong>{projectName}</strong>. Monitors real-time app permissions,
            tracks live file pushes, dispatches AI generation tasks, and enforces upstream rate-limit quotas.
          </p>
        </div>

        <div className="relay-metrics-cards">
          <div className="relay-metric-card" data-testid="metric-active-workers">
            <span className="metric-label">Active Background Tasks</span>
            <span className="metric-value">{inProgressCount}</span>
            <span className="metric-subtext">Executing non-stop</span>
          </div>
          <div className="relay-metric-card" data-testid="metric-completed-jobs">
            <span className="metric-label">Completed Works</span>
            <span className="metric-value text-emerald">{completedCount}</span>
            <span className="metric-subtext">Verified reports ready</span>
          </div>
          <div className="relay-metric-card" data-testid="metric-connected-apps">
            <span className="metric-label">Connected Apps</span>
            <span className="metric-value">{apps.filter((a) => a.status === 'connected').length} / {apps.length}</span>
            <span className="metric-subtext">Zero-trust permissions</span>
          </div>
        </div>
      </header>

      {/* ACTIVE REAL-TIME NOTIFICATION BANNER */}
      {activeAlert && (
        <div className="relay-alert-banner" role="alert" data-testid="relay-alert-banner">
          <div className="alert-content">
            <span className="alert-icon">⚡</span>
            <span className="alert-text">{activeAlert}</span>
          </div>
          <button
            className="alert-dismiss-btn"
            onClick={() => setActiveAlert(null)}
            aria-label="Dismiss alert"
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. REAL-TIME OPERATIONS GRID: GITHUB PUSH, CHATGPT GEN, AND RATE LIMIT COOLDOWN */}
      <section className="relay-live-operations-grid" aria-label="Live Operations">
        {/* OP 1: GITHUB LIVE FILE UPLOAD TRACKER */}
        <div className="relay-op-card github-op-card" data-testid="github-relay-card">
          <div className="op-card-header">
            <div className="op-service-info">
              <span className="op-service-icon">🐙</span>
              <div>
                <h3 className="op-service-name">GitHub Push Pipeline</h3>
                <span className="op-sub-meta">
                  Branch: <code>{githubPushState.branch}</code> · HEAD: <code>{githubPushState.commitSha}</code>
                </span>
              </div>
            </div>
            <span className={`status-tag ${githubPushState.isPushing ? 'busy' : 'synced'}`}>
              {githubPushState.isPushing ? 'PUSHING' : 'READY'}
            </span>
          </div>

          <div className="op-progress-section">
            <div className="op-progress-labels">
              <span className="op-progress-count" data-testid="github-files-count">
                <strong>{githubPushState.filesUploaded}</strong> of <strong>{githubPushState.totalFiles}</strong> files uploaded
              </span>
              <span className="op-progress-percentage" data-testid="github-upload-percent">
                {githubPercent}%
              </span>
            </div>

            <div className="relay-progress-track">
              <div
                className="relay-progress-fill emerald-fill"
                style={{ width: `${githubPercent}%` }}
                data-testid="github-progress-bar"
              ></div>
            </div>

            <div className="op-active-file-row">
              <span className="current-file-label">Current File:</span>
              <code className="current-file-name" title={githubPushState.currentFile}>
                {githubPushState.currentFile}
              </code>
            </div>

            <div className="op-telemetry-row">
              <span className="telemetry-item">Speed: <strong>{githubPushState.transferSpeed}</strong></span>
              <span className="telemetry-item">Destination: <strong>origin/{githubPushState.branch}</strong></span>
              <span className="telemetry-item">Checksums: <strong>SHA-256 Valid</strong></span>
            </div>
          </div>

          <div className="op-actions-row">
            <button
              className="relay-btn primary-btn"
              onClick={handleSimulateGitPush}
              disabled={githubPushState.isPushing}
              id="btn-simulate-git-push"
              data-testid="btn-simulate-git-push"
            >
              {githubPushState.isPushing ? 'Pushing Files...' : '🚀 Push Updates to GitHub'}
            </button>
            <span className="op-note">Simulates live multi-file progress bar</span>
          </div>
        </div>

        {/* OP 2: CHATGPT / DALL-E GENERATION & COMPLETION NOTIFIER */}
        <div className="relay-op-card ai-gen-op-card" data-testid="chatgpt-relay-card">
          <div className="op-card-header">
            <div className="op-service-info">
              <span className="op-service-icon">✨</span>
              <div>
                <h3 className="op-service-name">ChatGPT / DALL-E Job</h3>
                <span className="op-sub-meta">Autonomous Asset Generation</span>
              </div>
            </div>
            <span className={`status-tag ${imageGenState.isGenerating ? 'busy' : 'idle'}`}>
              {imageGenState.isGenerating ? 'GENERATING' : 'IDLE'}
            </span>
          </div>

          <div className="op-progress-section">
            <div className="ai-prompt-box">
              <span className="prompt-label">Prompt:</span>
              <p className="prompt-text">"{imageGenState.prompt}"</p>
            </div>

            <div className="op-progress-labels">
              <span className="op-progress-count" data-testid="image-gen-step">
                {imageGenState.stepDescription}
              </span>
              <span className="op-progress-percentage" data-testid="image-gen-percent">
                {imageGenState.progress}%
              </span>
            </div>

            <div className="relay-progress-track">
              <div
                className="relay-progress-fill cyan-fill"
                style={{ width: `${imageGenState.progress}%` }}
                data-testid="image-gen-progress-bar"
              ></div>
            </div>

            {/* Completed Asset Preview Card */}
            {imageGenState.progress === 100 && (
              <div className="completed-asset-preview" data-testid="image-completion-preview">
                <div className="asset-thumb-wrapper">
                  <img
                    src={imageGenState.completedAssetUrl}
                    alt="Obsidian 3D Mascot Orb Preview"
                    className="asset-thumbnail"
                  />
                  <span className="asset-ready-badge">Ready</span>
                </div>
                <div className="asset-details">
                  <span className="asset-name">Obsidian 3D Mascot Orb Concept.webp</span>
                  <span className="asset-meta">2048x2048 · WebP High-Res</span>
                  <button
                    className="asset-action-link"
                    onClick={() => setActiveAlert('📋 Asset link copied to clipboard!')}
                  >
                    Copy Asset Link
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="op-actions-row">
            <button
              className="relay-btn cyan-btn"
              onClick={handleSimulateImageGen}
              disabled={imageGenState.isGenerating}
              id="btn-simulate-image-gen"
              data-testid="btn-simulate-image-gen"
            >
              {imageGenState.isGenerating ? 'Synthesizing...' : '🎨 Trigger Image Generation'}
            </button>
            <span className="op-note">Dispatches completion alert upon finish</span>
          </div>
        </div>

        {/* OP 3: RATE LIMIT COOLDOWN & MODEL LIMIT REMINDER */}
        <div className="relay-op-card quota-op-card" data-testid="quota-relay-card">
          <div className="op-card-header">
            <div className="op-service-info">
              <span className="op-service-icon">⏳</span>
              <div>
                <h3 className="op-service-name">Model Quotas & Limits</h3>
                <span className="op-sub-meta">{rateLimitState.modelName}</span>
              </div>
            </div>
            <span className="status-tag warning">COOLDOWN</span>
          </div>

          <div className="quota-body">
            <div className="cooldown-notification-box" data-testid="cooldown-box">
              <div className="cooldown-headline">
                <span className="cooldown-icon">⚠️</span>
                <strong>Hourly Quota Reached</strong>
              </div>
              <p className="cooldown-message">
                Hourly generation threshold exhausted for this API token. Upstream providers enforce backoff cooldowns.
              </p>
              <div className="cooldown-timer-badge">
                <span>Resets after <strong>{rateLimitState.resetTimeLabel}</strong></span>
                <span className="countdown-pill">{formatCountdown(rateLimitState.remainingSeconds)} remaining</span>
              </div>
            </div>

            <div className="quota-meter-wrapper">
              <div className="quota-meter-header">
                <span className="quota-meter-title">Hourly Usage Counter:</span>
                <span className="quota-meter-numbers">
                  <strong>{rateLimitState.hourlyUsed}</strong> / {rateLimitState.hourlyLimit} Requests Used (96%)
                </span>
              </div>
              <div className="relay-progress-track">
                <div
                  className="relay-progress-fill amber-fill"
                  style={{ width: `${(rateLimitState.hourlyUsed / rateLimitState.hourlyLimit) * 100}%` }}
                ></div>
              </div>
            </div>

            <div className="quota-rule-callout">
              <span className="rule-badge">🛡️ Relay Strategy:</span>
              <p className="rule-desc">
                Tasks assigned during cooldown are automatically buffered in <strong>Queued</strong> status and
                will safely execute the instant the 10:00 AM window resets.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. ASSIGN TASK & CONNECTED APPS PERMISSION PANEL */}
      <section className="relay-management-row">
        {/* CONNECTED APPS & PERMISSIONS MANAGEMENT */}
        <div className="relay-section-box apps-permissions-box" data-testid="apps-permissions-box">
          <div className="section-title-row">
            <h3 className="section-title">
              <span className="section-icon">🔗</span> Connected Apps & Permissions
            </h3>
            <span className="section-badge">Zero-Trust Managed</span>
          </div>
          <p className="section-desc">
            Xeren Relay only executes actions explicitly permitted by your granted scopes. Toggle authorization at any time.
          </p>

          <div className="apps-list">
            {apps.map((app) => {
              const isConnected = app.status === 'connected'
              return (
                <div key={app.id} className={`app-card ${isConnected ? 'connected' : 'disconnected'}`}>
                  <div className="app-card-main">
                    <span className="app-icon">{app.icon}</span>
                    <div className="app-info">
                      <div className="app-name-row">
                        <h4 className="app-name">{app.name}</h4>
                        <span className={`connection-pill ${app.status}`}>
                          {app.status === 'connected' ? 'Connected' : 'Revoked'}
                        </span>
                      </div>
                      <p className="app-desc">{app.description}</p>
                      <div className="app-scopes-list">
                        <span className="scopes-label">Scopes:</span>
                        {app.permissions.map((perm) => (
                          <span key={perm} className="scope-chip">
                            {perm}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="app-card-actions">
                    <span className="app-account-meta">{app.activeAccount}</span>
                    <button
                      className={`relay-mini-toggle ${isConnected ? 'active' : 'inactive'}`}
                      onClick={() => handleToggleAppStatus(app.id)}
                      data-testid={`toggle-app-${app.id}`}
                    >
                      {isConnected ? 'Disconnect' : 'Authorize'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* DISPATCH NEW TASK TO RELAY */}
        <div className="relay-section-box dispatch-task-box">
          <div className="section-title-row">
            <h3 className="section-title">
              <span className="section-icon">📥</span> Assign Task to Xeren Relay
            </h3>
            <span className="section-badge">Autonomous Execution</span>
          </div>
          <p className="section-desc">
            Dispatch background routines to run silently while you continue working in your workstation.
          </p>

          <form className="dispatch-form" onSubmit={handleDispatchTask}>
            <div className="form-group">
              <label htmlFor="relay-task-input" className="form-label">
                Task Objective / Instruction
              </label>
              <input
                id="relay-task-input"
                type="text"
                className="relay-text-input"
                placeholder="e.g., Push release branch to GitHub and run full unit suite..."
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                data-testid="input-new-task-title"
              />
            </div>

            <div className="form-group">
              <label htmlFor="relay-target-select" className="form-label">
                Target Connected Service
              </label>
              <select
                id="relay-target-select"
                className="relay-select-input"
                value={newTaskTarget}
                onChange={(e) => setNewTaskTarget(e.target.value as any)}
                data-testid="select-task-target"
              >
                <option value="github">🐙 GitHub (File Push & Repo Operations)</option>
                <option value="chatgpt">✨ ChatGPT / DALL-E (Asset Generation & Reasoning)</option>
                <option value="figma">🎨 Figma (Design Tokens Sync)</option>
                <option value="runtime">⚡ Sandboxed Runtime (Test Suites & Builds)</option>
              </select>
            </div>

            <div className="preset-shortcuts">
              <span className="shortcuts-label">Quick Actions:</span>
              <button
                type="button"
                className="shortcut-pill"
                onClick={() => {
                  setNewTaskTitle('Push current branch to GitHub with automated checksums')
                  setNewTaskTarget('github')
                }}
              >
                + Git Push Task
              </button>
              <button
                type="button"
                className="shortcut-pill"
                onClick={() => {
                  setNewTaskTitle('Synthesize 4K UI Mockup with ChatGPT DALL-E')
                  setNewTaskTarget('chatgpt')
                }}
              >
                + Image Gen Task
              </button>
              <button
                type="button"
                className="shortcut-pill"
                onClick={() => {
                  setNewTaskTitle('Run Full Regression & Isolation Test Matrix')
                  setNewTaskTarget('runtime')
                }}
              >
                + Test Suite Task
              </button>
            </div>

            <button
              type="submit"
              className="relay-btn primary-btn submit-btn"
              disabled={!newTaskTitle.trim()}
              data-testid="btn-dispatch-task"
            >
              ⚡ Dispatch to Xeren Relay
            </button>
          </form>
        </div>
      </section>

      {/* 4. BACKGROUND TASKS ENGINE & COMPREHENSIVE WORK REPORTS */}
      <section className="relay-tasks-engine-section" data-testid="relay-tasks-section">
        <div className="tasks-header-bar">
          <div className="tasks-title-col">
            <h3 className="section-title">
              <span className="section-icon">📊</span> Background Execution Registry
            </h3>
            <span className="tasks-count-badge">{tasks.length} total tasks</span>
          </div>

          {/* Filter Pills */}
          <div className="task-filter-pills" role="tablist">
            <button
              className={`filter-pill ${taskFilter === 'all' ? 'active' : ''}`}
              onClick={() => setTaskFilter('all')}
              data-testid="filter-all"
            >
              All Tasks ({tasks.length})
            </button>
            <button
              className={`filter-pill ${taskFilter === 'in_progress' ? 'active' : ''}`}
              onClick={() => setTaskFilter('in_progress')}
              data-testid="filter-in-progress"
            >
              In Progress ({inProgressCount})
            </button>
            <button
              className={`filter-pill ${taskFilter === 'completed' ? 'active' : ''}`}
              onClick={() => setTaskFilter('completed')}
              data-testid="filter-completed"
            >
              Completed ({completedCount})
            </button>
            <button
              className={`filter-pill ${taskFilter === 'queued' ? 'active' : ''}`}
              onClick={() => setTaskFilter('queued')}
              data-testid="filter-queued"
            >
              Queued ({queuedCount})
            </button>
          </div>
        </div>

        {/* Task Cards List */}
        <div className="relay-tasks-list">
          {filteredTasks.map((task) => {
            const isExpanded = expandedTaskId === task.id
            const isCompleted = task.status === 'completed'
            const isInProgress = task.status === 'in_progress'

            return (
              <div
                key={task.id}
                className={`task-row-card ${task.status} ${isExpanded ? 'expanded' : ''}`}
                data-testid={`task-card-${task.id}`}
              >
                <div
                  className="task-summary-row"
                  onClick={() => setExpandedTaskId(isExpanded ? null : task.id)}
                >
                  <div className="task-id-col">
                    <span className="task-app-icon">
                      {task.appTarget === 'github' && '🐙'}
                      {task.appTarget === 'chatgpt' && '✨'}
                      {task.appTarget === 'figma' && '🎨'}
                      {task.appTarget === 'runtime' && '⚡'}
                    </span>
                    <span className="task-id">{task.id}</span>
                  </div>

                  <div className="task-content-col">
                    <h4 className="task-title">{task.title}</h4>
                    <span className="task-status-text">{task.statusText}</span>

                    {/* Progress Bar for in-progress tasks */}
                    {isInProgress && (
                      <div className="task-mini-progress">
                        <div
                          className="task-mini-fill"
                          style={{ width: `${task.progressPercent}%` }}
                        ></div>
                      </div>
                    )}
                  </div>

                  <div className="task-meta-col">
                    <span className={`task-badge ${task.status}`}>
                      {isInProgress && '⏳ In Progress'}
                      {isCompleted && '✅ Completed'}
                      {task.status === 'queued' && '⏱️ Queued'}
                    </span>
                    <span className="task-time">{task.timestamp}</span>
                    <button
                      className="expand-toggle-btn"
                      aria-label="Toggle Work Report"
                      title="View detailed work report"
                    >
                      {isExpanded ? '▲' : '▼'}
                    </button>
                  </div>
                </div>

                {/* COMPREHENSIVE WORK REPORT (EXPANDABLE) */}
                {isExpanded && task.report && (
                  <div className="task-work-report" data-testid={`work-report-${task.id}`}>
                    <div className="report-header">
                      <span className="report-title">📋 Work Report & Telemetry Verification</span>
                      <span className="report-duration">⏱️ Execution: {task.report.duration}</span>
                    </div>

                    <p className="report-summary">{task.report.outputSummary}</p>

                    {task.report.filesTouched && task.report.filesTouched.length > 0 && (
                      <div className="report-section">
                        <span className="report-section-label">Files Modified / Synced:</span>
                        <div className="report-files-chips">
                          {task.report.filesTouched.map((f) => (
                            <code key={f} className="file-chip">
                              {f}
                            </code>
                          ))}
                        </div>
                      </div>
                    )}

                    {task.report.testsPassed && (
                      <div className="report-section">
                        <span className="report-section-label">Verification Results:</span>
                        <span className="report-verification-tag">
                          🛡️ {task.report.testsPassed}
                        </span>
                      </div>
                    )}

                    <div className="report-section">
                      <span className="report-section-label">Security & Sandbox Audit:</span>
                      <span className="report-security-tag">
                        🔒 {task.report.securityAudit}
                      </span>
                    </div>

                    {task.report.artifactUrl && (
                      <div className="report-section artifact-row">
                        <a
                          href={task.report.artifactUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="report-artifact-link"
                        >
                          👁️ View Generated Asset Output
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
