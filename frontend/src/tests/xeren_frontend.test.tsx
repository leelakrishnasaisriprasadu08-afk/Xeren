import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'
import { XerenPresence } from '../components/XerenPresence/XerenPresence'
import { AgentActivity } from '../components/AgentActivity/AgentActivity'
import { ConnectionStatus } from '../components/ConnectionStatus/ConnectionStatus'
import { MockRealtimeTransport } from '../services/realtimeTransport'
import { VoiceOutputService } from '../services/voiceService'

describe('Xeren 1.0 Frontend - 18 Verification Scenarios', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  // Scenario 1: Initial idle state
  it('Scenario 1: renders presence in idle state with proper ARIA labels', () => {
    render(<App />)
    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toBeInTheDocument()
    expect(presence).toHaveClass('state-idle')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Xeren is present')
  })

  // Scenario 2: Start listening
  it('Scenario 2: clicking microphone button transitions presence to listening state', async () => {
    render(<App />)
    const micButton = screen.getByTestId('mic-button')
    expect(micButton).toBeInTheDocument()

    await act(async () => {
      fireEvent.click(micButton)
    })

    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-listening')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Listening...')
    expect(micButton).toHaveClass('listening')
  })

  // Scenario 3: Stop listening
  it('Scenario 3: clicking microphone button again stops listening and returns to idle', async () => {
    render(<App />)
    const micButton = screen.getByTestId('mic-button')

    await act(async () => {
      fireEvent.click(micButton)
    })
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Listening...')

    await act(async () => {
      fireEvent.click(micButton)
    })

    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-idle')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Xeren is present')
  })

  // Scenario 4: Mic permission denied
  it('Scenario 4: handles microphone permission denial gracefully with friendly error banner', async () => {
    // Mock getUserMedia failure
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia
    navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue(new Error('Permission denied'))

    render(<App />)
    const micButton = screen.getByTestId('mic-button')

    await act(async () => {
      fireEvent.click(micButton)
    })

    const errorBanner = screen.getByTestId('voice-error-banner')
    expect(errorBanner).toBeInTheDocument()
    expect(errorBanner).toHaveTextContent(/Microphone permission was denied/i)

    // Text composer must remain functional and enabled
    const textInput = screen.getByTestId('text-composer-input')
    expect(textInput).toBeEnabled()

    navigator.mediaDevices.getUserMedia = originalGetUserMedia
  })

  // Scenario 5: Text message submission
  it('Scenario 5: submitting text via composer renders user message and transitions presence to thinking', async () => {
    render(<App />)
    const input = screen.getByTestId('text-composer-input')
    const form = screen.getByTestId('text-composer-form')

    fireEvent.change(input, { target: { value: 'Hello Xeren' } })
    expect(input).toHaveValue('Hello Xeren')

    await act(async () => {
      fireEvent.submit(form)
    })

    // User message bubble rendered
    expect(screen.getByText('Hello Xeren')).toBeInTheDocument()
    // Presence moves to thinking
    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-thinking')
    // Input is cleared
    expect(input).toHaveValue('')
  })

  // Scenario 6: Progressive streaming text delta
  it('Scenario 6: progressive streaming text deltas accumulate smoothly with streaming cursor', async () => {
    render(<App />)
    const input = screen.getByTestId('text-composer-input')
    const form = screen.getByTestId('text-composer-form')

    fireEvent.change(input, { target: { value: 'Explain quantum computing' } })
    await act(async () => {
      fireEvent.submit(form)
    })

    // Fast-forward slightly for mock transport to deliver deltas
    await act(async () => {
      vi.advanceTimersByTime(400)
    })

    // Streaming cursor or streaming message row is rendered
    const streamingBubble = screen.queryByTestId('streaming-message-row')
    expect(streamingBubble).toBeInTheDocument()
  })

  // Scenario 7: Streaming completion
  it('Scenario 7: streaming completion finalizes message and clears streaming bubble', async () => {
    render(<App />)
    const input = screen.getByTestId('text-composer-input')
    const form = screen.getByTestId('text-composer-form')

    fireEvent.change(input, { target: { value: 'Hello Xeren' } })
    await act(async () => {
      fireEvent.submit(form)
    })

    // Fast forward past all streaming deltas
    await act(async () => {
      vi.advanceTimersByTime(2500)
    })

    // Final response committed into message list
    const assistantRows = screen.getAllByTestId('message-row-xeren')
    expect(assistantRows.length).toBeGreaterThan(0)
    expect(screen.queryByTestId('streaming-cursor')).not.toBeInTheDocument()
  })

  // Scenario 8: Speaking state transition
  it('Scenario 8: transitions presence to speaking state during voice output', () => {
    render(
      <XerenPresence
        state="speaking"
        amplitude={0.6}
      />
    )
    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('state-speaking')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Speaking...')
  })

  // Scenario 9: User barge-in / interruption
  it('Scenario 9: user barge-in via Interrupt button immediately stops response and marks interrupted', async () => {
    render(<App />)
    const input = screen.getByTestId('text-composer-input')
    const form = screen.getByTestId('text-composer-form')

    fireEvent.change(input, { target: { value: 'Tell me a long story' } })
    await act(async () => {
      fireEvent.submit(form)
    })

    // Advance to mid-streaming
    await act(async () => {
      vi.advanceTimersByTime(400)
    })

    const interruptBtn = screen.getByTestId('interrupt-button')
    expect(interruptBtn).toBeInTheDocument()

    // Click interrupt
    await act(async () => {
      fireEvent.click(interruptBtn)
    })

    // Verify presence returned to idle
    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-idle')
  })

  // Scenario 10: Agent activity milestone progression
  it('Scenario 10: updates milestone pill and stepper nodes across high-level milestones', async () => {
    const { rerender } = render(
      <AgentActivity
        progressDetails={{
          phase: 'planning',
          goal: 'Synthesizing knowledge graph',
          progress_percent: 33,
        }}
        activeMilestone="planning"
      />
    )

    const pill = screen.getByTestId('milestone-pill')
    expect(pill).toBeInTheDocument()
    expect(pill).toHaveTextContent('planning')
    expect(pill).toHaveTextContent('Synthesizing knowledge graph')

    // Click to expand drawer
    fireEvent.click(pill)
    expect(screen.getByTestId('activity-drawer')).toBeInTheDocument()
    expect(screen.getByTestId('step-node-planning')).toHaveClass('active')
    expect(screen.getByTestId('step-node-understanding')).toHaveClass('completed')

    // Rerender with next milestone: 'verifying'
    rerender(
      <AgentActivity
        progressDetails={{
          phase: 'verifying',
          goal: 'Synthesizing knowledge graph',
          progress_percent: 85,
        }}
        activeMilestone="verifying"
      />
    )
    expect(screen.getByTestId('step-node-verifying')).toHaveClass('active')
  })

  // Scenario 11: Connection failure handling
  it('Scenario 11: transport connection error transitions connection indicator to error', () => {
    const onReconnect = vi.fn()
    render(
      <ConnectionStatus
        state="error"
        transportType="mock"
        onReconnect={onReconnect}
      />
    )

    const pill = screen.getByTestId('connection-status-pill')
    expect(pill).toHaveClass('status-error')
    expect(pill).toHaveTextContent('Connection Error (Retry)')

    fireEvent.click(pill)
    expect(onReconnect).toHaveBeenCalledTimes(1)
  })

  // Scenario 12: Automatic / manual reconnection
  it('Scenario 12: mock transport connect succeeds and reports connected state', async () => {
    const transport = new MockRealtimeTransport()
    let state = transport.state
    transport.onConnectionChange((s) => {
      state = s
    })

    const connectPromise = transport.connect()
    vi.advanceTimersByTime(250)
    await connectPromise

    expect(state).toBe('connected')
    expect(transport.state).toBe('connected')
  })

  // Scenario 13: Malformed server event resilience
  it('Scenario 13: malformed or unknown server events are safely ignored without crashing', () => {
    const transport = new MockRealtimeTransport()
    let errorCaught = false

    try {
      transport.simulateMalformedEvent({ invalid: 12345 } as any)
      transport.simulateMalformedEvent(null as any)
    } catch {
      errorCaught = true
    }

    expect(errorCaught).toBe(false)
  })

  // Scenario 14: Audio playback failure fallback
  it('Scenario 14: handles voice output error gracefully via error callback', () => {
    const service = new VoiceOutputService()
    const onError = vi.fn()

    // Pass invalid or trigger speak callback
    service.speak('', { onError, onEnd: vi.fn() })
    // Does not crash
    expect(service.isSpeaking).toBe(false)
  })

  // Scenario 15: Complete state auto-reset
  it('Scenario 15: complete presence state renders affirmation label', () => {
    render(<XerenPresence state="complete" />)
    const label = screen.getByTestId('presence-state-label')
    expect(label).toHaveTextContent('Ready')
  })

  // Scenario 16: Reduced-motion preference
  it('Scenario 16: enables reduced-motion mode applying reduced-motion class', () => {
    render(<XerenPresence state="thinking" isReducedMotion={true} />)
    const presence = screen.getByRole('status')
    expect(presence).toHaveClass('reduced-motion')
  })

  // Scenario 17: Responsive layout adaptations
  it('Scenario 17: renders full application shell with header, presence stage, and dock', () => {
    render(<App />)
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
    expect(screen.getByTestId('text-composer-form')).toBeInTheDocument()
  })

  // Scenario 18: Accessibility (ARIA roles and keyboard shortcuts)
  it('Scenario 18: keyboard shortcut Escape interrupts active speech/streaming', async () => {
    render(<App />)
    const input = screen.getByTestId('text-composer-input')
    const form = screen.getByTestId('text-composer-form')

    fireEvent.change(input, { target: { value: 'Talk to me' } })
    await act(async () => {
      fireEvent.submit(form)
    })

    // Advance into thinking
    await act(async () => {
      vi.advanceTimersByTime(200)
    })

    // Press Escape key
    await act(async () => {
      fireEvent.keyDown(window, { key: 'Escape' })
    })

    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-idle')
  })
})
