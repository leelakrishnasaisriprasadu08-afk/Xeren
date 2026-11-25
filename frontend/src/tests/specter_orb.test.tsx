import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SpecterOrb } from '../components/SpecterOrb/SpecterOrb'
import { XerenSpecterOrb } from '../components/SpecterOrb/XerenSpecterOrb'
import { XerenPresence } from '../components/XerenPresence/XerenPresence'

describe('SpecterOrb & XerenSpecterOrb Component', () => {
  it('renders SpecterOrb with data-testid="specter-orb"', () => {
    render(<SpecterOrb />)
    const orb = screen.getByTestId('specter-orb')
    expect(orb).toBeInTheDocument()
    expect(orb).toHaveClass('specter-orb-container')
  })

  it('applies custom dimensions, className, and background', () => {
    render(
      <SpecterOrb
        width="400px"
        height="300px"
        className="custom-specter-class"
        backgroundColor="#050811"
      />
    )
    const orb = screen.getByTestId('specter-orb')
    expect(orb).toHaveClass('custom-specter-class')
    expect(orb.style.width).toBe('400px')
    expect(orb.style.height).toBe('300px')
  })

  it('renders stacked children inside SpecterOrb', () => {
    render(
      <SpecterOrb>
        <div data-testid="child-overlay">Overlay Content</div>
      </SpecterOrb>
    )
    expect(screen.getByTestId('child-overlay')).toHaveTextContent('Overlay Content')
  })

  it('handles pointer move and leave without crashing', () => {
    render(<SpecterOrb cursorInteraction={true} />)
    const orb = screen.getByTestId('specter-orb')

    fireEvent.pointerMove(orb, { clientX: 100, clientY: 50 })
    fireEvent.pointerLeave(orb)
    expect(orb).toBeInTheDocument()
  })

  it('renders XerenSpecterOrb with state-driven styling and amplitude modulation', () => {
    const { rerender } = render(
      <XerenSpecterOrb
        state="listening"
        amplitude={0.8}
      />
    )
    const orb = screen.getByTestId('specter-orb')
    expect(orb).toBeInTheDocument()

    // Test transition to thinking
    rerender(<XerenSpecterOrb state="thinking" amplitude={0.2} />)
    expect(orb).toBeInTheDocument()

    // Test speaking state
    rerender(<XerenSpecterOrb state="speaking" amplitude={0.9} />)
    expect(orb).toBeInTheDocument()

    // Test error state
    rerender(<XerenSpecterOrb state="error" />)
    expect(orb).toBeInTheDocument()
  })

  it('respects isReducedMotion on XerenSpecterOrb', () => {
    render(<XerenSpecterOrb state="idle" isReducedMotion={true} />)
    const orb = screen.getByTestId('specter-orb')
    expect(orb).toBeInTheDocument()
  })


  it('renders within XerenPresence by default as Specter Orb', () => {
    render(
      <XerenPresence
        state="listening"
        amplitude={0.7}
      />
    )
    expect(screen.getByTestId('xeren-presence')).toBeInTheDocument()
    expect(screen.getByTestId('presence-specter-orb')).toBeInTheDocument()
    expect(screen.getByTestId('specter-orb')).toBeInTheDocument()
    expect(screen.getByText('Listening...')).toBeInTheDocument()
  })

  it('renders Specter Orb directly in MainWorkspace without neural field switcher', async () => {
    const { MainWorkspace } = await import('../components/MainWorkspace/MainWorkspace')
    render(
      <MainWorkspace
        presenceState="idle"
        activeAmplitude={0}
        prefersReducedMotion={false}
        messages={[]}
        currentStreamingText=""
        currentStreamingId={null}
        agentProgress={null}
        activeMilestone={null}
        isListening={false}
        isSpeaking={false}
        voiceError={null}
        onSendMessage={vi.fn()}
        onStartListening={vi.fn()}
        onStopListening={vi.fn()}
        onInterrupt={vi.fn()}
      />
    )

    expect(screen.getByTestId('presence-specter-orb')).toBeInTheDocument()
    expect(screen.queryByTestId('presence-mode-selector')).not.toBeInTheDocument()
    expect(screen.queryByTestId('mode-btn-neural')).not.toBeInTheDocument()
  })

  it('renders Specter Orb preview inside LandingPage architecture modal', async () => {
    const { LandingPage } = await import('../components/LandingPage/LandingPage')
    render(<LandingPage />)
    const exploreBtn = screen.getByTestId('hero-secondary-cta')
    fireEvent.click(exploreBtn)
    expect(screen.getByTestId('arch-specter-orb-preview')).toBeInTheDocument()
  })
})

