import React, { useState, useEffect, useCallback, useRef } from 'react'
import { SpecterOrb } from '../SpecterOrb/SpecterOrb'
import './LandingPage.css'

export interface LandingPageProps {
  onEnterWorkspace?: () => void
  hlsStreamUrl?: string
  fallbackVideoUrl?: string
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onEnterWorkspace,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isMuted, setIsMuted] = useState(true)
  const [activeModal, setActiveModal] = useState<'architecture' | 'docs' | null>(null)
  const [activeSection, setActiveSection] = useState<string>('features')
  const [copiedDocsCode, setCopiedDocsCode] = useState(false)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
    if (e.key.toLowerCase() === 'm') {
      e.preventDefault()
      setIsMuted((prev) => !prev)
    } else if (e.key === 'Escape') {
      setActiveModal(null)
    }
  }, [])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Scroll reveal and active navigation section tracking
  useEffect(() => {
    const isTest =
      typeof window !== 'undefined' &&
      ((window as any).__VITEST__ ||
        (typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test'))

    // In test environment or if IntersectionObserver is absent, show all items immediately
    if (isTest || typeof IntersectionObserver === 'undefined') {
      const items = document.querySelectorAll('.scroll-reveal-item')
      items.forEach((item) => item.classList.add('is-visible'))
      return
    }

    const container = containerRef.current
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            const id = entry.target.getAttribute('id')
            if (id) {
              setActiveSection(id)
            }
          }
        })
      },
      {
        root: container || null,
        threshold: 0.1,
        rootMargin: '0px 0px -40px 0px',
      }
    )

    const revealItems = document.querySelectorAll('.scroll-reveal-item')
    revealItems.forEach((el) => observer.observe(el))

    // Direct scroll listener on container for smooth active nav tracking
    const handleScroll = () => {
      if (!container) return
      const sections = ['features', 'architecture', 'pipeline', 'benchmarks', 'docs', 'use-cases']
      const scrollTop = container.scrollTop
      for (let i = sections.length - 1; i >= 0; i--) {
        const sec = document.getElementById(sections[i])
        if (sec && scrollTop >= sec.offsetTop - 180) {
          setActiveSection(sections[i])
          break
        }
      }
    }

    container?.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      observer.disconnect()
      container?.removeEventListener('scroll', handleScroll)
    }
  }, [])

  const handleLaunch = () => {
    onEnterWorkspace?.()
  }

  const scrollToSection = (id: string) => {
    setActiveSection(id)
    const el = document.getElementById(id)
    const container = containerRef.current
    if (el) {
      if (typeof el.scrollIntoView === 'function') {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      } else if (container) {
        container.scrollTo({ top: el.offsetTop - 70, behavior: 'smooth' })
      }
    }
  }

  const copyDocsCode = () => {
    const code = `import { XerenClient } from '@xeren/sdk'\n\nconst client = new XerenClient({ ephemeral: true })\nconst session = await client.createSession({ mode: 'reasoning' })\nconst plan = await session.plan('Build verified price alert')\nawait session.execute(plan)`
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(code)
    }
    setCopiedDocsCode(true)
    setTimeout(() => setCopiedDocsCode(false), 2000)
  }

  return (
    <div
      ref={containerRef}
      className="landing-page-root emerald-theme"
      data-testid="landing-page"
    >
      {/* ── Background Atmosphere: Subtle Dot Grid + Radial Teals + Grain ── */}
      <div className="emerald-horizon-bg" aria-hidden="true">
        <div className="horizon-glow-radial" />
        <div className="horizon-subtle-grid" />
        <div className="horizon-beam-motif" />
        <div className="horizon-particle-drift" />
      </div>

      {/* ── 1. NAVBAR (Sticky, Translucent Glass with Active Scroll Indicators) ── */}
      <header className="emerald-nav-header">
        <div className="emerald-nav-brand">
          <div className="emerald-logo-mark" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <span className="logo-gem">❖</span>
            <span className="logo-text">XEREN</span>
          </div>
          <div className="emerald-model-badge">
            <span className="pulse-indicator" />
            <span className="badge-text">● XEREN AGENT v1.0</span>
          </div>
        </div>

        {/* Center / Right Links - All Scroll Smoothly to On-Page Sections */}
        <nav className="emerald-nav-links" aria-label="Quick Links">
          <button
            type="button"
            className={`nav-link-btn ${activeSection === 'features' ? 'active' : ''}`}
            onClick={() => scrollToSection('features')}
          >
            Features
          </button>
          <button
            type="button"
            className={`nav-link-btn ${activeSection === 'architecture' ? 'active' : ''}`}
            onClick={() => scrollToSection('architecture')}
          >
            Architecture
          </button>
          <button
            type="button"
            className={`nav-link-btn ${activeSection === 'pipeline' ? 'active' : ''}`}
            onClick={() => scrollToSection('pipeline')}
          >
            Pipeline
          </button>
          <button
            type="button"
            className={`nav-link-btn ${activeSection === 'benchmarks' ? 'active' : ''}`}
            onClick={() => scrollToSection('benchmarks')}
          >
            Benchmarks
          </button>
          <button
            type="button"
            className={`nav-link-btn ${activeSection === 'docs' ? 'active' : ''}`}
            onClick={() => scrollToSection('docs')}
          >
            Docs
          </button>
        </nav>

        <div className="emerald-nav-actions">
          <button
            type="button"
            className={`nav-audio-pill ${!isMuted ? 'unmuted' : ''}`}
            onClick={() => setIsMuted((prev) => !prev)}
            data-testid="hero-audio-pill"
            aria-label="Toggle Ambient Audio"
          >
            {!isMuted ? '● Sound On' : '○ Sound Off'}
          </button>

          <button
            type="button"
            className="nav-primary-btn"
            onClick={handleLaunch}
            data-testid="hero-primary-cta"
          >
            <span>Enter Workspace</span>
            <span className="btn-arrow">→</span>
          </button>
        </div>
      </header>

      {/* ── 2. HERO SECTION ── */}
      <section className="emerald-hero-section">
        {/* Diagonal Light Streak cutting through hero */}
        <div className="hero-comet-beam" aria-hidden="true" />

        <div className="hero-eyebrow">
          <span className="eyebrow-dot" />
          <span>● INTRODUCING XEREN · AGENTIC REASONING PLATFORM</span>
        </div>

        <h1 className="hero-main-title">
          <span className="title-white">Agents that plan,</span>
          <span className="title-gradient">retrieve, and verify.</span>
        </h1>

        <p className="hero-description">
          Plans multi-step tasks, retrieves grounded context via RAG, executes tools in secure environments,
          and verifies its own output before responding.
        </p>

        {/* Primary CTA Buttons */}
        <div className="hero-cta-group">
          <button
            type="button"
            className="hero-primary-launch-btn"
            onClick={handleLaunch}
            aria-label="Launch Neural Workspace"
          >
            <span>Launch Neural Workspace</span>
            <span className="cta-arrow">→</span>
          </button>

          <button
            type="button"
            className="hero-ghost-arch-btn"
            onClick={() => scrollToSection('architecture')}
          >
            <span>View Architecture</span>
            <span className="btn-down-arrow">↓</span>
          </button>
        </div>

        {/* Stat Pills Row */}
        <div className="hero-pill-strip">
          <div className="pill-card">
            <span className="pill-bullet">●</span>
            <span>1M Context Window</span>
          </div>
          <span className="pill-separator">·</span>
          <div className="pill-card">
            <span className="pill-bullet">●</span>
            <span>Retrieval-Native</span>
          </div>
          <span className="pill-separator">·</span>
          <div className="pill-card">
            <span className="pill-bullet">●</span>
            <span>Tool Execution</span>
          </div>
          <span className="pill-separator">·</span>
          <div className="pill-card">
            <span className="pill-bullet">●</span>
            <span>Self-Verifying</span>
          </div>
        </div>
      </section>

      {/* ── 3. TRUST & REPUTATION STRIP ── */}
      <section className="trust-strip-section scroll-reveal-item" aria-label="Trust Summary">
        <div className="trust-strip-inner">
          <span className="trust-strip-label">BUILT FOR RESEARCH, ENGINEERING &amp; ENTERPRISE OPS TEAMS</span>
          <div className="trust-badges-row">
            <span className="trust-badge-item">🛡️ 100% Zero-Data Retention</span>
            <span className="trust-badge-item">⚡ Deterministic Verification</span>
            <span className="trust-badge-item">🔍 Grounded Hybrid RAG</span>
            <span className="trust-badge-item">🔒 Sandboxed Tool Execution</span>
          </div>
        </div>
      </section>

      {/* ── 4. FEATURE GRID & HIGHLIGHT CARD (SCROLL REVEAL) ── */}
      <section id="features" className="features-grid-section scroll-reveal-item">
        <div className="section-header-block">
          <div className="section-eyebrow">AGENTIC CAPABILITIES</div>
          <h2 className="section-title">Engineered for autonomous cognitive precision</h2>
          <p className="section-subtitle">
            Beyond standard chatbots: a deterministic engine designed to plan, gather evidence, act, and verify.
          </p>
        </div>

        {/* SPECIAL HIGHLIGHT: ALL-IN-ONE PLACE [AI] */}
        <div className="featured-banner-card">
          <div className="featured-banner-badge">
            <span className="featured-sparkle">✦</span>
            <span>EXCLUSIVE AGENTIC STUDIO</span>
          </div>
          <h3 className="featured-banner-title">
            EASY ACCESS ALL IN ONE-PLACE <span className="highlight-ai">[AI]</span>
          </h3>
          <p className="featured-banner-desc">
            Seamlessly combine deep multi-step reasoning, instant document vector search, code execution,
            and task automation inside a single unified workspace. Zero tab jumping. Zero context loss.
          </p>
          <div className="featured-banner-tags">
            <span className="tag-pill">Unified Chat &amp; Deliberation</span>
            <span className="tag-pill">Autonomous Tool Execution</span>
            <span className="tag-pill">Knowledge Vault RAG</span>
            <span className="tag-pill">Voice Synthesis</span>
          </div>
        </div>

        {/* 4 Core Feature Cards */}
        <div className="features-quad-grid">
          {/* Feature 1 */}
          <div className="feature-panel-card">
            <div className="feature-icon-box">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
              </svg>
            </div>
            <h3 className="feature-card-title">Agentic Planning</h3>
            <p className="feature-card-text">
              Deconstructs complex, ambiguous objectives into ordered dependency trees, verifiable sub-milestones,
              and strategic decision paths.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="feature-panel-card">
            <div className="feature-icon-box">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                <ellipse cx="12" cy="5" rx="9" ry="3" />
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
              </svg>
            </div>
            <h3 className="feature-card-title">Native RAG Retrieval</h3>
            <p className="feature-card-text">
              Grounds generation in real-time documentation and enterprise vaults with hybrid semantic search,
              preventing hallucination with citations.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="feature-panel-card">
            <div className="feature-icon-box">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                <polyline points="4 17 10 11 4 5" />
                <line x1="12" y1="19" x2="20" y2="19" />
              </svg>
            </div>
            <h3 className="feature-card-title">Tool Execution</h3>
            <p className="feature-card-text">
              Directly executes APIs, queries databases, runs sandbox scripts, and inspects outputs under strict
              security boundaries.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="feature-panel-card">
            <div className="feature-icon-box">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <polyline points="9 12 11 14 15 10" />
              </svg>
            </div>
            <h3 className="feature-card-title">Adaptive Feedback Loop</h3>
            <p className="feature-card-text">
              Performs self-auditing verification checks against formal logic criteria, automatically correcting
              reasoning before delivery.
            </p>
          </div>
        </div>
      </section>

      {/* ── 5. SYSTEM ARCHITECTURE SHOWCASE (DIRECT ON-PAGE SCROLL SECTION) ── */}
      <section id="architecture" className="architecture-showcase-section scroll-reveal-item" aria-label="System Architecture">
        <div className="section-header-block">
          <div className="section-eyebrow">SYSTEM ARCHITECTURE &amp; NEURAL SPECIFICATION</div>
          <h2 className="section-title">Autonomous Neural Engine &amp; Reasoning Core</h2>
          <p className="section-subtitle">
            Direct hardware-accelerated deduction, spatial cognitive modeling, and real-time verifiable proofs.
          </p>
        </div>

        <div className="architecture-showcase-grid">
          {/* Card 1: SpecterOrb 3D Interactive Latent Cognitive Core */}
          <div className="arch-showcase-card arch-card-specter">
            <div
              className="arch-specter-preview"
              data-testid={!activeModal ? 'arch-specter-orb-preview' : undefined}
            >
              <SpecterOrb
                width="100%"
                height="100%"
                radius={0.3}
                turbulence={0.22}
                flowSpeed={0.08}
                maskRadius={0}
                maskFeather={0.3}
                zoom={0.88}
                glowStrength={1.3}
                colorA="#10b981"
                colorB="#059669"
                colorC="#34d399"
                backgroundColor="transparent"
              />
            </div>
            <div className="arch-card-header">
              <span className="arch-badge">LATENT COGNITIVE CORE</span>
              <div className="arch-card-icon">🧠</div>
            </div>
            <h3 className="arch-card-heading">Latent Cognitive Core</h3>
            <p className="arch-card-description">
              Multi-step reasoning architecture trained specifically for spatial deduction, mathematical decomposition,
              and pattern induction. Operates over an ultra-low latency continuous token manifold.
            </p>
            <div className="arch-feature-pills">
              <span>Dynamic Reasoning Paths</span>
              <span>Spatial Token Projection</span>
              <span>Self-Audited Milestones</span>
            </div>
          </div>

          {/* Card 2: Photonic Glow Cursor */}
          <div
            className="arch-showcase-card"
            data-testid={!activeModal ? 'arch-glow-cursor-card' : undefined}
          >
            <div className="arch-card-header">
              <span className="arch-badge">INTERACTION PHYSICS</span>
              <div className="arch-card-icon">✨</div>
            </div>
            <h3 className="arch-card-heading">Photonic Glow Cursor</h3>
            <p className="arch-card-description">
              Hardware-accelerated luminescence tracking pointer velocity with subtle emerald emission falloff.
              Responsive spatial awareness keeps user intent grounded across multi-modal interfaces.
            </p>
            <div className="arch-mini-preview-glow">
              <div className="glow-cursor-trail-dot dot-1" />
              <div className="glow-cursor-trail-dot dot-2" />
              <div className="glow-cursor-trail-dot dot-3" />
              <span className="glow-telemetry-tag">Sub-1ms Tracking Latency</span>
            </div>
          </div>

          {/* Card 3: Autonomous Verification Engine */}
          <div className="arch-showcase-card">
            <div className="arch-card-header">
              <span className="arch-badge">ZERO-ERROR GATING</span>
              <div className="arch-card-icon">⚡</div>
            </div>
            <h3 className="arch-card-heading">Autonomous Verification Engine</h3>
            <p className="arch-card-description">
              Automated runtime testing logical consistency, code correctness, and evidence-grounded proofs before output.
              Employs formal verification barriers to eliminate hallucinations.
            </p>
            <div className="arch-verification-checks">
              <div className="arch-check-line">
                <span className="check-icon">✓</span>
                <span>Deterministic Proof Validation</span>
              </div>
              <div className="arch-check-line">
                <span className="check-icon">✓</span>
                <span>Sandboxed Dynamic Execution</span>
              </div>
              <div className="arch-check-line">
                <span className="check-icon">✓</span>
                <span>Automated Self-Auditing Feedback</span>
              </div>
            </div>
          </div>

          {/* Card 4: Zero-Leak Privacy */}
          <div className="arch-showcase-card">
            <div className="arch-card-header">
              <span className="arch-badge">ENTERPRISE SECURITY</span>
              <div className="arch-card-icon">🛡️</div>
            </div>
            <h3 className="arch-card-heading">Zero-Leak Ephemeral Privacy</h3>
            <p className="arch-card-description">
              100% ephemeral state handling and verified zero data retention policy across all layers. Cryptographic key
              rotation and instant RAM destruction upon session close.
            </p>
            <div className="arch-retention-badge-box">
              <span className="retention-dot" />
              <span>Certified Zero-Data Retention Guarantee</span>
            </div>
          </div>
        </div>

        {/* Modal Dialog Option for Deep-Dive Specs */}
        <div className="arch-deep-dive-bar">
          <span className="deep-dive-text">Need complete low-level architectural specs and modal blueprint?</span>
          <button
            type="button"
            className="arch-deep-dive-btn"
            onClick={() => setActiveModal('architecture')}
            data-testid="hero-secondary-cta"
          >
            <span>Open Architecture Blueprint Dialog</span>
            <span className="btn-arrow">↗</span>
          </button>
        </div>
      </section>

      {/* ── 6. EXECUTION PIPELINE (CONNECTED PIPELINE STRIP) ── */}
      <section id="pipeline" className="architecture-pipeline-section scroll-reveal-item">
        <div className="section-header-block">
          <div className="section-eyebrow">EXECUTION PIPELINE</div>
          <h2 className="section-title">How Xeren reasons through tasks</h2>
          <p className="section-subtitle">
            Deterministic sequence from user input to verified production output.
          </p>
        </div>

        <div className="pipeline-nodes-container">
          {/* Node 1 */}
          <div className="pipeline-node-card">
            <div className="node-step-index">01</div>
            <div className="node-icon-wrap">📥</div>
            <div className="node-title">Input</div>
            <div className="node-desc">Goal ingestion &amp; constraint parsing</div>
          </div>

          <div className="pipeline-connector-line">
            <span className="connector-pulse" />
          </div>

          {/* Node 2 */}
          <div className="pipeline-node-card">
            <div className="node-step-index">02</div>
            <div className="node-icon-wrap">🗺️</div>
            <div className="node-title">Planner</div>
            <div className="node-desc">DAG milestone task decomposition</div>
          </div>

          <div className="pipeline-connector-line">
            <span className="connector-pulse" />
          </div>

          {/* Node 3 */}
          <div className="pipeline-node-card">
            <div className="node-step-index">03</div>
            <div className="node-icon-wrap">🔍</div>
            <div className="node-title">Retriever (RAG)</div>
            <div className="node-desc">Grounding in private &amp; web vaults</div>
          </div>

          <div className="pipeline-connector-line">
            <span className="connector-pulse" />
          </div>

          {/* Node 4 */}
          <div className="pipeline-node-card">
            <div className="node-step-index">04</div>
            <div className="node-icon-wrap">⚙️</div>
            <div className="node-title">Tool Execution</div>
            <div className="node-desc">Sandboxed APIs, shell, &amp; code run</div>
          </div>

          <div className="pipeline-connector-line">
            <span className="connector-pulse" />
          </div>

          {/* Node 5 */}
          <div className="pipeline-node-card node-highlight">
            <div className="node-step-index">05</div>
            <div className="node-icon-wrap">🛡️</div>
            <div className="node-title">Verifier</div>
            <div className="node-desc">Self-checking tests &amp; logical audit</div>
          </div>

          <div className="pipeline-connector-line">
            <span className="connector-pulse" />
          </div>

          {/* Node 6 */}
          <div className="pipeline-node-card">
            <div className="node-step-index">06</div>
            <div className="node-icon-wrap">✨</div>
            <div className="node-title">Output</div>
            <div className="node-desc">Verified synthesized solution</div>
          </div>
        </div>
      </section>

      {/* ── 7. BENCHMARKS / METRICS STRIP ── */}
      <section id="benchmarks" className="benchmarks-strip-section scroll-reveal-item">
        <div className="benchmarks-inner-grid">
          <div className="metric-cell">
            <div className="metric-large-number">140+</div>
            <div className="metric-label">Tokens / Sec Throughput</div>
            <div className="metric-caption">Ultra-low latency streaming</div>
          </div>

          <div className="metric-cell">
            <div className="metric-large-number">99.4%</div>
            <div className="metric-label">Verified Output Accuracy</div>
            <div className="metric-caption">Grounded in deterministic checks</div>
          </div>

          <div className="metric-cell">
            <div className="metric-large-number">&lt;120ms</div>
            <div className="metric-label">Planning Latency</div>
            <div className="metric-caption">Real-time DAG task generation</div>
          </div>

          <div className="metric-cell">
            <div className="metric-large-number">1,000,000</div>
            <div className="metric-label">Token Context Window</div>
            <div className="metric-caption">Full repository &amp; doc comprehension</div>
          </div>
        </div>
      </section>

      {/* ── 8. DEVELOPER DOCUMENTATION SHOWCASE (DIRECT ON-PAGE SCROLL SECTION) ── */}
      <section id="docs" className="docs-showcase-section scroll-reveal-item" aria-label="Developer Documentation">
        <div className="section-header-block">
          <div className="section-eyebrow">DEVELOPER DOCUMENTATION &amp; SDK REFERENCE</div>
          <h2 className="section-title">Build with XEREN Autonomous Core</h2>
          <p className="section-subtitle">
            Simple SDK setup, WebSocket/Realtime RPC, and deterministic sandbox tool contracts.
          </p>
        </div>

        <div className="docs-showcase-grid">
          {/* Docs Card 1: Getting Started */}
          <div className="docs-panel-card">
            <div className="docs-panel-badge">
              <span className="docs-badge-icon">🚀</span>
              <span>GETTING STARTED</span>
            </div>
            <h3 className="docs-card-title">Initiate Autonomous Agent Sessions</h3>
            <p className="docs-card-text">
              Launch the workspace to initiate a natural reasoning session. Speak naturally via microphone or stream
              complex multi-step prompts directly through the TypeScript and Python SDKs.
            </p>
            <div className="docs-code-container">
              <div className="docs-code-header">
                <span className="code-lang-tag">TypeScript SDK</span>
                <button
                  type="button"
                  className="code-copy-btn"
                  onClick={copyDocsCode}
                  title="Copy code snippet"
                >
                  {copiedDocsCode ? '✓ Copied' : '📋 Copy'}
                </button>
              </div>
              <pre className="docs-code-block">
                <code>{`import { XerenClient } from '@xeren/sdk'

const client = new XerenClient({ ephemeral: true })
const session = await client.createSession({ mode: 'reasoning' })
const plan = await session.plan('Build verified price alert')
await session.execute(plan)`}</code>
              </pre>
            </div>
          </div>

          {/* Docs Card 2: Multi-Step Tool Verification */}
          <div className="docs-panel-card">
            <div className="docs-panel-badge">
              <span className="docs-badge-icon">⚙️</span>
              <span>TOOL INTEGRATION</span>
            </div>
            <h3 className="docs-card-title">Multi-Step Tool Verification</h3>
            <p className="docs-card-text">
              XEREN automatically plans tasks, queries connected knowledge vaults via RAG, invokes sandboxed tools,
              and self-checks every output before returning it.
            </p>
            <ul className="docs-points-list">
              <li>
                <strong>DAG Milestone Decomposition:</strong> Breaks ambiguous objectives into ordered dependencies.
              </li>
              <li>
                <strong>Ephemeral Sandboxes:</strong> Tools execute in RAM-isolated environments with zero leak.
              </li>
              <li>
                <strong>Self-Checking Assertions:</strong> Verifies proof consistency before reporting answers.
              </li>
            </ul>
          </div>

          {/* Docs Card 3: Zero Data Retention */}
          <div className="docs-panel-card">
            <div className="docs-panel-badge">
              <span className="docs-badge-icon">🔒</span>
              <span>SECURITY ARCHITECTURE</span>
            </div>
            <h3 className="docs-card-title">Zero Data Retention Architecture</h3>
            <p className="docs-card-text">
              All conversations and ephemeral states are processed locally and in temporary memory buffers without persistent retention.
            </p>
            <div className="docs-security-matrix">
              <div className="sec-matrix-row">
                <span className="sec-matrix-label">Session Memory:</span>
                <span className="sec-matrix-val">RAM-only, destroyed on disconnect</span>
              </div>
              <div className="sec-matrix-row">
                <span className="sec-matrix-label">Knowledge Vault:</span>
                <span className="sec-matrix-val">Local Chroma / Qdrant instance</span>
              </div>
              <div className="sec-matrix-row">
                <span className="sec-matrix-label">External Telemetry:</span>
                <span className="sec-matrix-val">100% Zero third-party logging</span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="docs-footer-cta">
          <button
            type="button"
            className="docs-workspace-btn"
            onClick={handleLaunch}
          >
            <span>Launch Neural Workspace &amp; Test Live</span>
            <span className="btn-arrow">→</span>
          </button>
        </div>
      </section>

      {/* ── 9. ENTERPRISE APPLICATIONS / USE CASES ── */}
      <section id="use-cases" className="use-cases-section scroll-reveal-item">
        <div className="section-header-block">
          <div className="section-eyebrow">ENTERPRISE APPLICATIONS</div>
          <h2 className="section-title">Engineered for mission-critical workflows</h2>
          <p className="section-subtitle">
            How forward-thinking engineering and research teams deploy Xeren.
          </p>
        </div>

        <div className="use-cases-grid">
          <div className="use-case-card">
            <div className="use-case-badge">RESEARCH ASSISTANTS</div>
            <h3 className="use-case-title">Deep Technical Synthesis</h3>
            <p className="use-case-text">
              Accelerate literature exploration across thousands of papers and datasets. Generates grounded
              summaries with traceable citations, ensuring rigorous adherence to evidence.
            </p>
            <div className="use-case-benefit">✓ Traceable evidence citations</div>
          </div>

          <div className="use-case-card">
            <div className="use-case-badge">ENGINEERING COPILOTS</div>
            <h3 className="use-case-title">Autonomous Code &amp; Debugging</h3>
            <p className="use-case-text">
              Deconstruct complex architecture migrations into atomic sub-tasks. Executes test suites,
              analyzes runtime error traces, and validates builds before generating pull requests.
            </p>
            <div className="use-case-benefit">✓ Test-verified code changes</div>
          </div>

          <div className="use-case-card">
            <div className="use-case-badge">ENTERPRISE OPS</div>
            <h3 className="use-case-title">Internal Knowledge Automation</h3>
            <p className="use-case-text">
              Connect private data vaults, internal APIs, and databases. Automate compliance auditing,
              operational incident triaging, and workflow orchestration under strict zero-leak policies.
            </p>
            <div className="use-case-benefit">✓ Zero data retention guarantee</div>
          </div>
        </div>
      </section>

      {/* ── 10. FINAL CTA BANNER ── */}
      <section className="final-cta-section scroll-reveal-item">
        <div className="final-cta-panel">
          <div className="final-cta-glow-backdrop" aria-hidden="true" />
          <div className="final-cta-content">
            <span className="final-cta-eyebrow">START REASONING TODAY</span>
            <h2 className="final-cta-heading">
              Ready to deploy autonomous agentic intelligence?
            </h2>
            <p className="final-cta-subheading">
              Experience the power of planning, grounded RAG retrieval, sandboxed tools, and self-verification.
            </p>
            <button
              type="button"
              className="final-cta-button"
              onClick={handleLaunch}
            >
              <span>Launch Neural Workspace</span>
              <span className="btn-arrow">→</span>
            </button>
          </div>
        </div>
      </section>

      {/* ── 11. FOOTER ── */}
      <footer className="emerald-footer">
        <div className="footer-top-grid">
          <div className="footer-brand-col">
            <div className="footer-logo">
              <span className="logo-gem">❖</span>
              <span className="logo-text">XEREN</span>
            </div>
            <p className="footer-tagline">
              Autonomous agentic reasoning engine engineered for verified execution and zero-retention privacy.
            </p>
            <div className="footer-retention-pill">
              <span>🔒 100% Zero-Data Retention</span>
            </div>
          </div>

          <div className="footer-links-col">
            <h4>Platform</h4>
            <ul>
              <li><button type="button" onClick={() => scrollToSection('features')}>Agent Planner</button></li>
              <li><button type="button" onClick={() => scrollToSection('pipeline')}>Native RAG</button></li>
              <li><button type="button" onClick={() => scrollToSection('features')}>Tool Sandbox</button></li>
              <li><button type="button" onClick={() => scrollToSection('benchmarks')}>Verification Engine</button></li>
            </ul>
          </div>

          <div className="footer-links-col">
            <h4>Architecture</h4>
            <ul>
              <li><button type="button" onClick={() => scrollToSection('architecture')}>System Overview</button></li>
              <li><button type="button" onClick={() => scrollToSection('benchmarks')}>Benchmarks</button></li>
              <li><button type="button" onClick={() => scrollToSection('use-cases')}>Enterprise Security</button></li>
              <li><button type="button" onClick={() => scrollToSection('docs')}>API Documentation</button></li>
            </ul>
          </div>

          <div className="footer-links-col">
            <h4>Company</h4>
            <ul>
              <li><a href="#about" onClick={(e) => e.preventDefault()}>About Xeren</a></li>
              <li><a href="#research" onClick={(e) => e.preventDefault()}>Research Papers</a></li>
              <li><a href="#privacy" onClick={(e) => e.preventDefault()}>Privacy &amp; Ephemeral Policy</a></li>
              <li><a href="#contact" onClick={(e) => e.preventDefault()}>Contact Labs</a></li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom-bar">
          <span>© 2026 XEREN Neural Labs · All rights reserved.</span>
          <div className="footer-bottom-tags">
            <span>Ephemeral State</span>
            <span>·</span>
            <span>Deterministic Verification</span>
            <span>·</span>
            <span>Enterprise Ready</span>
          </div>
        </div>
      </footer>

      {/* ── Architecture Modal (Deep-Dive Dialog) ── */}
      {activeModal === 'architecture' && (
        <div
          className="landing-modal-backdrop"
          onClick={() => setActiveModal(null)}
          role="dialog"
          aria-modal="true"
          data-testid="landing-modal"
        >
          <div
            className="landing-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div className="modal-title-group">
                <span className="modal-category">SYSTEM ARCHITECTURE</span>
                <h2 className="modal-title">Autonomous Neural Engine &amp; Reasoning Core</h2>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setActiveModal(null)}
                aria-label="Close dialog"
                data-testid="modal-close-btn"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="architecture-grid">
                <div className="arch-card arch-card-specter">
                  <div className="arch-specter-preview" data-testid="arch-specter-orb-preview">
                    <SpecterOrb
                      width="100%"
                      height="100%"
                      radius={0.3}
                      turbulence={0.22}
                      flowSpeed={0.08}
                      maskRadius={0}
                      maskFeather={0.3}
                      zoom={0.88}
                      glowStrength={1.3}
                      colorA="#10b981"
                      colorB="#059669"
                      colorC="#34d399"
                      backgroundColor="transparent"
                    />
                  </div>
                  <div className="arch-card-icon">🧠</div>
                  <h3>Latent Cognitive Core</h3>
                  <p>Multi-step reasoning architecture trained specifically for spatial deduction, mathematical decomposition, and pattern induction.</p>
                </div>

                <div className="arch-card" data-testid="arch-glow-cursor-card">
                  <div className="arch-card-icon">✨</div>
                  <h3>Photonic Glow Cursor</h3>
                  <p>Hardware-accelerated luminescence tracking pointer velocity with subtle emerald emission falloff.</p>
                </div>

                <div className="arch-card">
                  <div className="arch-card-icon">⚡</div>
                  <h3>Autonomous Verification Engine</h3>
                  <p>Automated runtime testing logical consistency, code correctness, and evidence-grounded proofs before output.</p>
                </div>

                <div className="arch-card">
                  <div className="arch-card-icon">🛡️</div>
                  <h3>Zero-Leak Privacy</h3>
                  <p>100% ephemeral state handling and verified zero data retention policy across all layers.</p>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="modal-enter-btn"
                onClick={() => {
                  setActiveModal(null)
                  onEnterWorkspace?.()
                }}
              >
                Enter Neural Workspace →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Docs Modal (Deep-Dive Dialog) ── */}
      {activeModal === 'docs' && (
        <div
          className="landing-modal-backdrop"
          onClick={() => setActiveModal(null)}
          role="dialog"
          aria-modal="true"
          data-testid="landing-modal"
        >
          <div
            className="landing-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div className="modal-title-group">
                <span className="modal-category">DOCUMENTATION</span>
                <h2 className="modal-title">XEREN Developer Reference</h2>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setActiveModal(null)}
                aria-label="Close dialog"
                data-testid="modal-close-btn"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="docs-content">
                <div className="docs-section">
                  <h3>Getting Started</h3>
                  <p>Launch the workspace to initiate a natural reasoning session. You can speak naturally via microphone or input complex multi-step prompts.</p>
                </div>
                <div className="docs-section">
                  <h3>Multi-Step Tool Verification</h3>
                  <p>XEREN automatically plans tasks, queries connected knowledge vaults via RAG, invokes tools, and self-checks every output before returning it.</p>
                </div>
                <div className="docs-section">
                  <h3>Zero Data Retention</h3>
                  <p>All conversations and ephemeral states are processed locally and in temporary memory buffers without persistent retention.</p>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="modal-enter-btn"
                onClick={() => {
                  setActiveModal(null)
                  onEnterWorkspace?.()
                }}
              >
                Enter Workspace →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LandingPage
