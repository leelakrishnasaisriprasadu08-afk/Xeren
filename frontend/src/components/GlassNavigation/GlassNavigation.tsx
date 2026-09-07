import React, { useState, useEffect } from 'react'
import './GlassNavigation.css'

export interface GlassNavigationProps {
  onEnterWorkspace?: () => void
  onOpenDocs?: () => void
  isMuted?: boolean
  onToggleMute?: () => void
  brandTitle?: string
}

export const GlassNavigation: React.FC<GlassNavigationProps> = ({
  onEnterWorkspace,
  onOpenDocs,
  isMuted = true,
  onToggleMute,
  brandTitle = 'XEREN',
}) => {
  const [scrolled, setScrolled] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const navLinks = [
    { label: 'Capabilities', href: '#capabilities' },
    { label: 'Neural Core', href: '#neural-core' },
    { label: 'Architecture', href: '#architecture' },
    { label: 'Benchmarks', href: '#benchmarks' },
  ]

  return (
    <header
      className={`glass-nav-container ${scrolled ? 'is-scrolled' : ''}`}
      data-testid="glass-nav-header"
    >
      <div className="glass-nav-pill">
        {/* Brand Identity */}
        <div className="glass-nav-brand" onClick={onEnterWorkspace} role="button" tabIndex={0}>
          <div className="brand-logo-mark">
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
              <path
                d="M16 3L28 10V22L16 29L4 22V10L16 3Z"
                stroke="#00f0ff"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="16" cy="16" r="4" fill="#00f0ff" className="brand-nucleus" />
              <path d="M12 16L16 12L20 16L16 20Z" fill="white" />
            </svg>
          </div>
          <div className="brand-text-group">
            <span className="brand-name">{brandTitle}</span>
            <span className="brand-version-pill">v2.0</span>
          </div>
        </div>

        {/* Center Desktop Navigation Links */}
        <nav className="glass-nav-links" aria-label="Main Navigation">
          {navLinks.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="glass-nav-item"
              onClick={(e) => {
                e.preventDefault()
                const target = document.querySelector(item.href)
                if (target) {
                  target.scrollIntoView({ behavior: 'smooth' })
                }
              }}
            >
              <span>{item.label}</span>
              <div className="glass-nav-indicator" />
            </a>
          ))}
        </nav>

        {/* Right Actions / CTA */}
        <div className="glass-nav-actions">
          {/* Quick Sound/Mute Toggle */}
          {onToggleMute && (
            <button
              type="button"
              className={`glass-sound-toggle ${!isMuted ? 'active' : ''}`}
              onClick={onToggleMute}
              title={isMuted ? 'Unmute video stream sound' : 'Mute video stream sound'}
              aria-label={isMuted ? 'Unmute video stream sound' : 'Mute video stream sound'}
              data-testid="nav-sound-toggle"
            >
              {isMuted ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 5L6 9H2v6h4l5 4V5z" />
                  <line x1="23" y1="9" x2="17" y2="15" />
                  <line x1="17" y1="9" x2="23" y2="15" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 5L6 9H2v6h4l5 4V5z" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
                </svg>
              )}
            </button>
          )}

          {/* Secondary Docs Button */}
          {onOpenDocs && (
            <button
              type="button"
              className="glass-secondary-btn"
              onClick={onOpenDocs}
              data-testid="nav-docs-btn"
            >
              Docs
            </button>
          )}

          {/* Primary Action Button: Enter Workspace */}
          <button
            type="button"
            className="glass-primary-cta"
            onClick={onEnterWorkspace}
            data-testid="enter-workspace-btn"
          >
            <span className="cta-glow-pulse" />
            <span className="cta-text">Enter Workspace</span>
            <svg
              className="cta-arrow"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </button>

          {/* Mobile Menu Hamburger */}
          <button
            type="button"
            className="glass-hamburger-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
            aria-expanded={mobileMenuOpen}
            data-testid="glass-nav-hamburger"
          >
            <span className={`hamburger-bar ${mobileMenuOpen ? 'open-1' : ''}`} />
            <span className={`hamburger-bar ${mobileMenuOpen ? 'open-2' : ''}`} />
          </button>
        </div>
      </div>

      {/* Mobile Glassmorphic Drawer Menu */}
      <div
        className={`glass-mobile-drawer ${mobileMenuOpen ? 'is-open' : ''}`}
        aria-hidden={!mobileMenuOpen}
      >
        <div className="mobile-drawer-content">
          {navLinks.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="mobile-drawer-item"
              onClick={() => setMobileMenuOpen(false)}
            >
              {item.label}
            </a>
          ))}
          <button
            type="button"
            className="mobile-drawer-cta"
            onClick={() => {
              setMobileMenuOpen(false)
              onEnterWorkspace?.()
            }}
          >
            Enter Workspace
          </button>
        </div>
      </div>
    </header>
  )
}
export default GlassNavigation
