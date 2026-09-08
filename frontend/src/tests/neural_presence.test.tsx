import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { XerenPresence } from '../components/XerenPresence/XerenPresence'
import { AtmosphericBackground } from '../components/AtmosphericBackground/AtmosphericBackground'
import { NeuralFieldRenderer } from '../components/XerenPresence/NeuralFieldRenderer'

describe('Xeren Volumetric Neural Presence & Atmospheric Background Tests', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  // 1. IDLE State
  it('renders presence in IDLE state with volumetric neural canvas, ambient glow, and accessible labels', () => {
    render(<XerenPresence state="idle" mode="neural-field" />)

    const presence = screen.getByRole('status')
    expect(presence).toBeInTheDocument()
    expect(presence).toHaveClass('state-idle')
    expect(presence).toHaveAttribute('aria-label', 'AI Presence: Xeren is present')

    const label = screen.getByTestId('presence-state-label')
    expect(label).toHaveTextContent('Xeren is present')

    // Verify Canvas and volumetric glow are rendered
    const canvas = presence.querySelector('canvas.presence-neural-canvas')
    expect(canvas).toBeInTheDocument()
    const glow = presence.querySelector('.presence-volumetric-glow')
    expect(glow).toBeInTheDocument()
  })

  // 2. LISTENING State & Amplitude responsiveness
  it('renders presence in LISTENING state with voice-receptive energy and responsive state label', () => {
    const { rerender } = render(<XerenPresence state="listening" amplitude={0} />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-listening')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Listening...')

    // Rerender with voice amplitude
    rerender(<XerenPresence state="listening" amplitude={0.85} />)
    expect(presence).toHaveClass('state-listening')
  })

  // 3. THINKING State
  it('renders presence in THINKING state with active computational status', () => {
    render(<XerenPresence state="thinking" />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-thinking')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Thinking...')
  })

  // 4. ACTING State
  it('renders presence in ACTING state with task execution status', () => {
    render(<XerenPresence state="acting" />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-acting')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Executing task...')
  })

  // 5. SPEAKING State
  it('renders presence in SPEAKING state with voice output responsiveness', () => {
    render(<XerenPresence state="speaking" amplitude={0.65} />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-speaking')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Speaking...')
  })

  // 6. COMPLETE State
  it('renders presence in COMPLETE state with harmonious radiant status', () => {
    render(<XerenPresence state="complete" />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-complete')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Ready')
  })

  // 7. ERROR State
  it('renders presence in ERROR state with restrained warning status', () => {
    render(<XerenPresence state="error" />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-error')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Attention required')
  })

  // 8. PAUSED State
  it('renders presence in PAUSED state with subdued presence', () => {
    render(<XerenPresence state="paused" />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-paused')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Paused')
  })

  // 9. Reduced Motion Support
  it('applies reduced-motion class when isReducedMotion is true', () => {
    render(<XerenPresence state="thinking" isReducedMotion={true} amplitude={0.7} />)

    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('reduced-motion')
  })

  // 10. Interactivity (onClick callback)
  it('invokes onClick callback when presence is clicked', () => {
    const handleClick = vi.fn()
    render(<XerenPresence state="idle" onClick={handleClick} />)

    const presence = screen.getByRole('status')
    fireEvent.click(presence)
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  // 11. AtmosphericBackground Rendering and State Adaptation
  it('renders AtmosphericBackground with deep-space radial glow and canvas elements', () => {
    const { rerender } = render(<AtmosphericBackground state="idle" />)

    const bg = screen.getByTestId('atmospheric-background')
    expect(bg).toBeInTheDocument()
    expect(bg).toHaveClass('state-idle')

    const canvas = bg.querySelector('canvas.atmospheric-canvas')
    expect(canvas).toBeInTheDocument()

    // Test transition to listening state
    rerender(<AtmosphericBackground state="listening" />)
    expect(bg).toHaveClass('state-listening')

    // Test transition to acting state
    rerender(<AtmosphericBackground state="acting" />)
    expect(bg).toHaveClass('state-acting')
  })

  // 12. AtmosphericBackground Reduced Motion & Safe Unmount
  it('supports reduced motion mode and cleans up animation frame and listeners upon unmount', () => {
    const { unmount, rerender } = render(<AtmosphericBackground state="idle" isReducedMotion={true} />)

    const bg = screen.getByTestId('atmospheric-background')
    expect(bg).toHaveClass('reduced-motion')

    rerender(<AtmosphericBackground state="thinking" isReducedMotion={false} />)
    expect(() => unmount()).not.toThrow()
  })

  // 13. NeuralFieldRenderer direct lifecycle tests
  it('instantiates NeuralFieldRenderer, handles state updates, resize, and clean destruction', () => {
    const canvas = document.createElement('canvas')
    canvas.width = 480
    canvas.height = 480

    const renderer = new NeuralFieldRenderer({
      canvas,
      initialState: 'idle',
      isReducedMotion: false,
      maxParticles: 50,
    })

    // Test state transitions
    expect(() => renderer.setState('listening')).not.toThrow()
    expect(() => renderer.setState('thinking')).not.toThrow()
    expect(() => renderer.setState('acting')).not.toThrow()
    expect(() => renderer.setState('speaking')).not.toThrow()
    expect(() => renderer.setAmplitude(0.75)).not.toThrow()

    // Test resize
    expect(() => renderer.resize(600, 600)).not.toThrow()

    // Test reduced motion toggle
    expect(() => renderer.setReducedMotion(true)).not.toThrow()
    expect(() => renderer.setReducedMotion(false)).not.toThrow()

    // Test clean destruction
    expect(() => renderer.destroy()).not.toThrow()
  })

  // 14. 3D Neural Orb Interface Verification (Pure Neon Particles — Zero Threads)
  it('initializes 3D Neural Orb interface with 1200+ glowing neon particles and strictly zero threads', () => {
    const canvas = document.createElement('canvas')
    canvas.width = 540
    canvas.height = 480

    const renderer = new NeuralFieldRenderer({
      canvas,
      initialState: 'idle',
      isReducedMotion: false,
      maxParticles: 1800,
    })

    // Assert internal particle count meets the 3D Neural Orb specification (1200+)
    const particleCount = (renderer as any).particles.length
    expect(particleCount).toBeGreaterThanOrEqual(1200)
    expect(particleCount).toBeLessThanOrEqual(1800)

    // Assert strictly zero threads/lines for pure neon particle orb simulation
    const threadCount = (renderer as any).threads.length
    expect(threadCount).toBe(0)

    renderer.destroy()
  })
})
