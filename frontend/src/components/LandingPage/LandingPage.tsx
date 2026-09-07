import React, { useState, useEffect, useCallback } from 'react'
import { HlsVideoBackground } from '../HlsVideoBackground/HlsVideoBackground'
import { GlassNavigation } from '../GlassNavigation/GlassNavigation'
import { HeroBottomLeft } from '../HeroBottomLeft/HeroBottomLeft'
import { SpecterOrb } from '../SpecterOrb/SpecterOrb'
import './LandingPage.css'

export interface LandingPageProps {
  onEnterWorkspace?: () => void
  hlsStreamUrl?: string
  fallbackVideoUrl?: string
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onEnterWorkspace,
  hlsStreamUrl = 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',
  fallbackVideoUrl = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
}) => {
  const [isMuted, setIsMuted] = useState(true)
  const [isPlaying, setIsPlaying] = useState(true)
  const [activeModal, setActiveModal] = useState<'architecture' | 'docs' | null>(null)

  // Keyboard controls: M to toggle mute, Space to play/pause
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

    if (e.key.toLowerCase() === 'm') {
      e.preventDefault()
      setIsMuted((prev) => !prev)
    } else if (e.code === 'Space') {
      e.preventDefault()
      setIsPlaying((prev) => !prev)
    } else if (e.key === 'Escape') {
      setActiveModal(null)
    }
  }, [])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <main className="landing-page-root" data-testid="landing-page">
      {/* 1. Full-screen HLS Video Background */}
      <HlsVideoBackground
        src={hlsStreamUrl}
        fallbackSrc={fallbackVideoUrl}
        isMuted={isMuted}
        isPlaying={isPlaying}
        onToggleMute={(val) => setIsMuted(val)}
        onTogglePlay={(val) => setIsPlaying(val)}
        overlayIntensity="deep"
      />

      {/* 2. Glassmorphic Navigation Header */}
      <GlassNavigation
        onEnterWorkspace={onEnterWorkspace}
        onOpenDocs={() => setActiveModal('docs')}
        isMuted={isMuted}
        onToggleMute={() => setIsMuted((prev) => !prev)}
        brandTitle="XEREN"
      />

      {/* 3. Hero Content Positioned in Bottom-Left Corner */}
      <HeroBottomLeft
        onEnterWorkspace={onEnterWorkspace}
        onExploreFeatures={() => setActiveModal('architecture')}
        isMuted={isMuted}
        onToggleMute={() => setIsMuted((prev) => !prev)}
      />

      {/* Architecture / Capabilities Glass Modal */}
      {activeModal && (
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
                <h2 className="modal-title">
                  {activeModal === 'architecture' ? 'Autonomous Neural Engine' : 'Documentation & API'}
                </h2>
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
              {activeModal === 'architecture' ? (
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
                        colorA="#00f0ff"
                        colorB="#a855f7"
                        colorC="#3b82f6"
                        backgroundColor="transparent"
                      />
                    </div>
                    <div className="arch-card-icon">🔮</div>
                    <h3>Volumetric Specter Presence</h3>
                    <p>Ghostly raymarched Specter Orb wrapped in drifting smoke reacting dynamically to speech and cognitive states.</p>
                  </div>
                  <div className="arch-card" data-testid="arch-glow-cursor-card">
                    <div className="arch-card-icon">✨</div>
                    <h3>Photonic Glow Cursor</h3>
                    <p>GPU-accelerated raymarched luminescence trail following pointer dynamics with inverse-square falloff and smooth idle decay.</p>
                  </div>
                  <div className="arch-card">
                    <div className="arch-card-icon">⚡</div>
                    <h3>Full-Screen HLS Stream</h3>
                    <p>Adaptive bitrate HTTP Live Streaming powered by HLS.js with automatic network tier negotiation and hardware GPU decoding.</p>
                  </div>
                  <div className="arch-card">
                    <div className="arch-card-icon">🤖</div>
                    <h3>Autonomous Tool Agents</h3>
                    <p>Live search, code generation, browser automation, and local file exploration orchestrated via asynchronous event streams.</p>
                  </div>
                  <div className="arch-card">
                    <div className="arch-card-icon">🛡️</div>
                    <h3>Zero-Leak Privacy</h3>
                    <p>Strict local state retention, client-side audio rendering, and configurable WebSocket / Mock gateway transports.</p>
                  </div>
                </div>
              ) : (
                <div className="docs-preview">
                  <p>
                    Xeren 2.0 combines real-time streaming audio synthesis, visual presence fields,
                    and autonomous agentic pipelines.
                  </p>
                  <pre className="docs-code-snippet">
                    <code>{`// Initialize Xeren Neural Session\nconst session = await Xeren.connect({\n  transport: 'websocket',\n  videoStream: 'hls',\n  voiceReceptive: true\n});`}</code>
                  </pre>
                </div>
              )}
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
    </main>
  )
}
export default LandingPage
