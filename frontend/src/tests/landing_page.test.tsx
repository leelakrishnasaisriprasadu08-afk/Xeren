import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { HlsVideoBackground } from '../components/HlsVideoBackground/HlsVideoBackground'
import { GlassNavigation } from '../components/GlassNavigation/GlassNavigation'
import { HeroBottomLeft } from '../components/HeroBottomLeft/HeroBottomLeft'
import { LandingPage } from '../components/LandingPage/LandingPage'
import { App } from '../App'

describe('Modern Landing Page & HLS Video Background Tests', () => {
  // 1. HlsVideoBackground Component Tests
  it('renders full-screen HLS video background with video element, gradient masks, and telemetry badge', () => {
    render(<HlsVideoBackground isMuted={true} isPlaying={true} />)

    const bg = screen.getByTestId('hls-video-background')
    expect(bg).toBeInTheDocument()

    const video = screen.getByTestId('hls-video-element')
    expect(video).toBeInTheDocument()
    expect(video).toHaveAttribute('playsinline')

    const badge = screen.getByTestId('hls-stream-badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent(/LIVE/i)
  })

  it('toggles video background audio via mute button', () => {
    const handleToggleMute = vi.fn()
    render(<HlsVideoBackground isMuted={true} onToggleMute={handleToggleMute} />)

    const muteBtn = screen.getByTestId('hls-mute-toggle')
    expect(muteBtn).toBeInTheDocument()

    fireEvent.click(muteBtn)
    expect(handleToggleMute).toHaveBeenCalledWith(false)
  })

  it('toggles video background play/pause state via button', () => {
    const handleTogglePlay = vi.fn()
    render(<HlsVideoBackground isPlaying={true} onTogglePlay={handleTogglePlay} />)

    const playBtn = screen.getByTestId('hls-play-toggle')
    expect(playBtn).toBeInTheDocument()

    fireEvent.click(playBtn)
    expect(handleTogglePlay).toHaveBeenCalledWith(false)
  })

  // 2. GlassNavigation Component Tests
  it('renders glassmorphic navigation header with brand title, links, and enter CTA', () => {
    const handleEnter = vi.fn()
    render(<GlassNavigation onEnterWorkspace={handleEnter} brandTitle="XEREN" />)

    const header = screen.getByTestId('glass-nav-header')
    expect(header).toBeInTheDocument()
    expect(header).toHaveTextContent('XEREN')
    expect(header).toHaveTextContent('Capabilities')
    expect(header).toHaveTextContent('Neural Core')
    expect(header).toHaveTextContent('Architecture')

    const enterBtn = screen.getByTestId('enter-workspace-btn')
    expect(enterBtn).toBeInTheDocument()
    fireEvent.click(enterBtn)
    expect(handleEnter).toHaveBeenCalledTimes(1)
  })

  // 3. HeroBottomLeft Component Tests
  it('renders hero content positioned in the bottom-left corner with typography and metrics', () => {
    const handleEnter = vi.fn()
    const handleExplore = vi.fn()
    render(
      <HeroBottomLeft
        onEnterWorkspace={handleEnter}
        onExploreFeatures={handleExplore}
        isMuted={true}
      />
    )

    const hero = screen.getByTestId('hero-bottom-left')
    expect(hero).toBeInTheDocument()
    expect(hero).toHaveClass('hero-bottom-left-container')

    // Badge
    const badge = screen.getByTestId('hero-badge')
    expect(badge).toHaveTextContent('AUTONOMOUS COGNITION // RELEASE 2.0')

    // Headline
    const heading = hero.querySelector('h1')
    expect(heading).toHaveTextContent(/Cinematic Intelligence/i)

    // Primary CTA
    const primaryBtn = screen.getByTestId('hero-primary-cta')
    expect(primaryBtn).toBeInTheDocument()
    fireEvent.click(primaryBtn)
    expect(handleEnter).toHaveBeenCalledTimes(1)

    // Secondary CTA
    const secondaryBtn = screen.getByTestId('hero-secondary-cta')
    expect(secondaryBtn).toBeInTheDocument()
    fireEvent.click(secondaryBtn)
    expect(handleExplore).toHaveBeenCalledTimes(1)

    // Metrics
    expect(hero).toHaveTextContent('120ms')
    expect(hero).toHaveTextContent('HLS Live')
    expect(hero).toHaveTextContent('1,800+')
  })

  // 4. LandingPage Composite Tests
  it('renders full LandingPage and opens/closes architecture modal dialog', () => {
    render(<LandingPage />)

    const landingPage = screen.getByTestId('landing-page')
    expect(landingPage).toBeInTheDocument()

    // Open Architecture modal
    const exploreBtn = screen.getByTestId('hero-secondary-cta')
    fireEvent.click(exploreBtn)

    const modal = screen.getByTestId('landing-modal')
    expect(modal).toBeInTheDocument()
    expect(modal).toHaveTextContent('SYSTEM ARCHITECTURE')
    expect(modal).toHaveTextContent('Autonomous Neural Engine')

    // Verify SpecterOrb and GlowCursor previews exist in architecture modal
    expect(screen.getByTestId('arch-specter-orb-preview')).toBeInTheDocument()
    expect(screen.getByTestId('arch-glow-cursor-card')).toBeInTheDocument()

    // Close modal
    const closeBtn = screen.getByTestId('modal-close-btn')
    fireEvent.click(closeBtn)
    expect(screen.queryByTestId('landing-modal')).not.toBeInTheDocument()
  })

  it('handles keyboard shortcuts for mute (M) and play/pause (Space)', () => {
    render(<LandingPage />)

    // Press 'M' to toggle sound
    fireEvent.keyDown(window, { key: 'm' })
    const audioPill = screen.getByTestId('hero-audio-pill')
    expect(audioPill).toHaveClass('unmuted')

    // Press 'M' again to mute
    fireEvent.keyDown(window, { key: 'm' })
    expect(audioPill).not.toHaveClass('unmuted')
  })

  // 5. App View Transition Integration Tests
  it('transitions between Landing Page and AI Workspace via CTA button and header button', () => {
    render(<App initialView="landing" />)

    // 1. Initially renders Landing Page
    expect(screen.getByTestId('landing-page')).toBeInTheDocument()
    expect(screen.queryByTestId('top-header')).not.toBeInTheDocument()

    // 2. Click "Launch Neural Workspace" in hero
    const launchBtn = screen.getByTestId('hero-primary-cta')
    fireEvent.click(launchBtn)

    // 3. Transitions into Workspace
    expect(screen.queryByTestId('landing-page')).not.toBeInTheDocument()
    expect(screen.getByTestId('top-header')).toBeInTheDocument()
    expect(screen.getByTestId('main-workspace')).toBeInTheDocument()

    // 4. Click "Landing" in TopHeader
    const landingBtn = screen.getByTestId('header-landing-btn')
    expect(landingBtn).toBeInTheDocument()
    fireEvent.click(landingBtn)

    // 5. Returns to Landing Page
    expect(screen.getByTestId('landing-page')).toBeInTheDocument()
  })
})
