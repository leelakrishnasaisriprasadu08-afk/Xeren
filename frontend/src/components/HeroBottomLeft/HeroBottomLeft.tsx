import React from 'react'
import './HeroBottomLeft.css'

export interface HeroBottomLeftProps {
  onEnterWorkspace?: () => void
  onExploreFeatures?: () => void
  isMuted?: boolean
  onToggleMute?: () => void
}

export const HeroBottomLeft: React.FC<HeroBottomLeftProps> = ({
  onEnterWorkspace,
  onExploreFeatures,
  isMuted,
  onToggleMute,
}) => {
  return (
    <section
      className="hero-bottom-left-container"
      data-testid="hero-bottom-left"
      aria-label="Hero Overview"
    >
      {/* 1. Monospace Status Badge */}
      <div className="hero-telemetry-badge" data-testid="hero-badge">
        <span className="telemetry-radar-dot" />
        <span className="telemetry-badge-text">AUTONOMOUS COGNITION // RELEASE 2.0</span>
      </div>

      {/* 2. Bold Cyber-Editorial Headline */}
      <h1 className="hero-main-heading">
        Cinematic <span className="text-gradient-cyan">Intelligence</span>.
        <br />
        Engineered for Action.
      </h1>

      {/* 3. High-readability Description */}
      <p className="hero-description">
        Experience seamless multimodal reasoning with acoustic-reactive neural fields,
        real-time streaming intelligence, and autonomous browser execution.
      </p>

      {/* 4. Action Button Group */}
      <div className="hero-actions-group">
        <button
          type="button"
          className="hero-primary-btn"
          onClick={onEnterWorkspace}
          data-testid="hero-primary-cta"
        >
          <span className="btn-ambient-glow" />
          <span className="btn-label">Launch Neural Workspace</span>
          <svg
            className="btn-arrow-icon"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>

        {onExploreFeatures && (
          <button
            type="button"
            className="hero-secondary-btn"
            onClick={onExploreFeatures}
            data-testid="hero-secondary-cta"
          >
            <span>Explore Architecture</span>
          </button>
        )}

        {onToggleMute && (
          <button
            type="button"
            className={`hero-audio-pill ${!isMuted ? 'unmuted' : ''}`}
            onClick={onToggleMute}
            aria-label={isMuted ? 'Enable video audio' : 'Mute video audio'}
            title={isMuted ? 'Enable video audio' : 'Mute video audio'}
            data-testid="hero-audio-pill"
          >
            <span className="audio-wave-bars">
              <span className="bar bar-1" />
              <span className="bar bar-2" />
              <span className="bar bar-3" />
            </span>
            <span>{isMuted ? 'Sound Off' : 'Sound On'}</span>
          </button>
        )}
      </div>

      {/* 5. Live Architecture Metrics Row */}
      <div className="hero-telemetry-row">
        <div className="telemetry-metric-item">
          <span className="metric-val">120ms</span>
          <span className="metric-lbl">P99 Latency</span>
        </div>
        <div className="telemetry-divider" />
        <div className="telemetry-metric-item">
          <span className="metric-val">HLS Live</span>
          <span className="metric-lbl">60 FPS Feed</span>
        </div>
        <div className="telemetry-divider" />
        <div className="telemetry-metric-item">
          <span className="metric-val">1,800+</span>
          <span className="metric-lbl">Neural Dots</span>
        </div>
        <div className="telemetry-divider" />
        <div className="telemetry-metric-item">
          <span className="metric-val">100%</span>
          <span className="metric-lbl">Local Privacy</span>
        </div>
      </div>
    </section>
  )
}
export default HeroBottomLeft
