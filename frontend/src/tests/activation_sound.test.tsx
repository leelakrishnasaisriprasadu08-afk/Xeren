import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'
import {
  ActivationSoundService,
  stopActivationSound,
} from '../services/activationSound'
import * as activationSoundModule from '../services/activationSound'

describe('Xeren Neural Wake Activation Sound Tests', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
    stopActivationSound()
  })

  afterEach(() => {
    stopActivationSound()
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // 1. Activation invokes sound
  it('activation invokes sound synthesis', async () => {
    const service = new ActivationSoundService()
    const onAmplitude = vi.fn()
    const onEnd = vi.fn()

    const playPromise = service.playActivationSound({ onAmplitude, onEnd })
    expect(service.isPlaying).toBe(true)

    // Advance time through KLAK (0–120ms) and VMMMM (80–450ms)
    act(() => {
      vi.advanceTimersByTime(200)
    })

    // Advance past total duration (~800ms)
    act(() => {
      vi.advanceTimersByTime(650)
    })

    await playPromise
    expect(service.isPlaying).toBe(false)
    expect(onEnd).toHaveBeenCalledTimes(1)
  })

  // 2. Duplicate activation does not overlap sounds
  it('duplicate activation does not overlap sounds or start parallel instances', async () => {
    const service = new ActivationSoundService()
    const onEnd1 = vi.fn()
    const onEnd2 = vi.fn()

    const firstPlay = service.playActivationSound({ onEnd: onEnd1 })
    expect(service.isPlaying).toBe(true)

    // Second activation while first is playing
    const secondPlay = service.playActivationSound({ onEnd: onEnd2 })

    // Second call should return immediately without overriding
    await secondPlay
    expect(onEnd2).not.toHaveBeenCalled()

    // Complete first play
    act(() => {
      vi.advanceTimersByTime(850)
    })
    await firstPlay

    expect(onEnd1).toHaveBeenCalledTimes(1)
    expect(service.isPlaying).toBe(false)
  })

  // 3. Activation reaches LISTENING
  it('activation reaches LISTENING state in UI while sound activates', async () => {
    render(<App />)
    const micButton = screen.getByTestId('mic-button')

    await act(async () => {
      fireEvent.click(micButton)
    })

    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-listening')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Listening...')
  })

  // 4. Audio failure does not break activation
  it('audio failure does not break activation or microphone listening', async () => {
    // Mock playActivationSound rejection to simulate audio failure
    const playSpy = vi
      .spyOn(activationSoundModule, 'playActivationSound')
      .mockRejectedValueOnce(new Error('Autoplay blocked'))

    render(<App />)
    const micButton = screen.getByTestId('mic-button')

    // Click mic to activate
    await act(async () => {
      fireEvent.click(micButton)
    })

    // Microphone listening must proceed cleanly to LISTENING state
    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-listening')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Listening...')
    expect(playSpy).toHaveBeenCalled()
  })

  // 5. Interrupt stops active activation audio
  it('interrupt stops active activation audio immediately', async () => {
    const service = new ActivationSoundService()
    const onEnd = vi.fn()

    service.playActivationSound({ onEnd })
    expect(service.isPlaying).toBe(true)

    // Stop / interrupt mid-flight
    service.stopActivationSound()
    expect(service.isPlaying).toBe(false)

    // In UI: clicking mic then pressing Escape stops wake
    render(<App />)
    const micButton = screen.getByTestId('mic-button')

    await act(async () => {
      fireEvent.click(micButton)
    })
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Listening...')

    // Barge-in / Interrupt via Escape key
    await act(async () => {
      fireEvent.keyDown(window, { key: 'Escape' })
    })

    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-idle')
  })

  // 6. Reduced-motion mode remains functional
  it('reduced-motion mode remains functional and plays activation sound', async () => {
    render(<App />)

    // Open settings to enable reduced motion
    const settingsButton = screen.getByTestId('settings-button')
    fireEvent.click(settingsButton)

    const reducedMotionSelect = screen.getByTestId('reduced-motion-select')
    fireEvent.change(reducedMotionSelect, { target: { value: 'reduce' } })

    const closeBtn = screen.getByTestId('close-menu-button')
    fireEvent.click(closeBtn)

    // Verify container has reduced-motion class
    const container = document.querySelector('.app-container')
    expect(container).toHaveClass('reduced-motion')

    // Activate voice
    const micButton = screen.getByTestId('mic-button')
    await act(async () => {
      fireEvent.click(micButton)
    })

    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-listening')
    expect(screen.getByTestId('presence-state-label')).toHaveTextContent('Listening...')
  })
})
