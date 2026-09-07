/**
 * Xeren Neural Wake Activation Sound Service
 *
 * Synthesizes the distinctive Xeren activation sonic signature using Web Audio API:
 *   KLAK  (0–120ms)   : Crisp digital/metallic transient
 *   VMMMM (80–450ms)  : Smooth rising neural tone
 *   TII   (420–500ms) : First harmonic chime
 *   TII   (530–610ms) : Second harmonic chime
 *   TIIING(630–800ms) : Bright, crystal-harmonic resonance
 *
 * Total Duration: ~800ms (0.8s)
 */

export interface ActivationSoundCallbacks {
  onAmplitude?: (amplitude: number) => void
  onEnd?: () => void
  onError?: (error: Error) => void
}

export class ActivationSoundService {
  private audioContext: AudioContext | null = null
  private isPlayingState: boolean = false
  private activeNodes: Array<{ stop?: (time?: number) => void; disconnect?: () => void }> = []
  private animationFrameId: number | null = null
  private timeoutId: any = null

  /**
   * Check if activation sound is currently in flight.
   */
  public get isPlaying(): boolean {
    return this.isPlayingState
  }

  /**
   * Acquire or create a shared AudioContext instance safely.
   */
  private getOrCreateAudioContext(): AudioContext | null {
    if (typeof window === 'undefined') return null
    const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext
    if (!AudioCtxClass) return null

    try {
      if (!this.audioContext || this.audioContext.state === 'closed') {
        this.audioContext = new AudioCtxClass()
      }
      return this.audioContext
    } catch {
      return null
    }
  }

  /**
   * Play the Neural Wake activation sequence: KLAK → VMMMM → TII → TII → TIIIING
   *
   * Prevents overlapping sounds and handles browser autoplay restrictions gracefully.
   */
  public async playActivationSound(callbacks?: ActivationSoundCallbacks): Promise<void> {
    // Prevent overlapping activations immediately
    if (this.isPlayingState) {
      return
    }

    this.isPlayingState = true
    this.activeNodes = []

    const ctx = this.getOrCreateAudioContext()
    if (!ctx) {
      this.cleanup()
      callbacks?.onEnd?.()
      return
    }

    try {
      if (ctx.state === 'suspended') {
        await ctx.resume().catch(() => {})
      }
    } catch {
      // Graceful fallback if autoplay blocked
    }

    try {
      const now = ctx.currentTime || 0
      const masterGain = ctx.createGain()
      // Master volume kept conservative to maintain subtle, premium presence
      masterGain.gain.setValueAtTime(0.2, now)
      masterGain.connect(ctx.destination)
      this.activeNodes.push(masterGain)

      // =========================================================================
      // 1. KLAK (0–120ms): Crisp digital/metallic mechanical latch transient
      // =========================================================================
      const clickOsc = ctx.createOscillator()
      const clickGain = ctx.createGain()
      const clickFilter = ctx.createBiquadFilter()

      clickOsc.type = 'triangle'
      clickOsc.frequency.setValueAtTime(1900, now)
      if (clickOsc.frequency.exponentialRampToValueAtTime) {
        clickOsc.frequency.exponentialRampToValueAtTime(220, now + 0.05)
      }

      clickFilter.type = 'bandpass'
      clickFilter.frequency.setValueAtTime(1400, now)

      clickGain.gain.setValueAtTime(0.001, now)
      if (clickGain.gain.linearRampToValueAtTime) {
        clickGain.gain.linearRampToValueAtTime(0.35, now + 0.006)
      }
      if (clickGain.gain.exponentialRampToValueAtTime) {
        clickGain.gain.exponentialRampToValueAtTime(0.001, now + 0.09)
      }

      clickOsc.connect(clickFilter)
      clickFilter.connect(clickGain)
      clickGain.connect(masterGain)

      clickOsc.start(now)
      clickOsc.stop(now + 0.1)
      this.activeNodes.push(clickOsc, clickGain, clickFilter)

      // =========================================================================
      // 2. VMMMM (80–450ms): Smooth rising neural resonant tone
      // =========================================================================
      const riseOsc = ctx.createOscillator()
      const riseGain = ctx.createGain()
      const riseFilter = ctx.createBiquadFilter()

      riseOsc.type = 'sine'
      riseOsc.frequency.setValueAtTime(130, now + 0.06)
      if (riseOsc.frequency.exponentialRampToValueAtTime) {
        riseOsc.frequency.exponentialRampToValueAtTime(320, now + 0.42)
      }

      riseFilter.type = 'lowpass'
      riseFilter.frequency.setValueAtTime(240, now + 0.06)
      if (riseFilter.frequency.linearRampToValueAtTime) {
        riseFilter.frequency.linearRampToValueAtTime(850, now + 0.4)
      }

      riseGain.gain.setValueAtTime(0.001, now + 0.06)
      if (riseGain.gain.linearRampToValueAtTime) {
        riseGain.gain.linearRampToValueAtTime(0.28, now + 0.24)
        riseGain.gain.linearRampToValueAtTime(0.04, now + 0.44)
      }

      riseOsc.connect(riseFilter)
      riseFilter.connect(riseGain)
      riseGain.connect(masterGain)

      riseOsc.start(now + 0.06)
      riseOsc.stop(now + 0.46)
      this.activeNodes.push(riseOsc, riseGain, riseFilter)

      // =========================================================================
      // 3. TII → TII → TIIIING (420–800ms): Three harmonic signature tones
      // =========================================================================
      const chimes = [
        { freq: 880, start: now + 0.42, dur: 0.08, peak: 0.22 }, // A5
        { freq: 1108, start: now + 0.53, dur: 0.08, peak: 0.24 }, // C#6
        { freq: 1396, start: now + 0.63, dur: 0.17, peak: 0.3 }, // F6 (longer & brighter)
      ]

      chimes.forEach(({ freq, start, dur, peak }) => {
        const chimeOsc = ctx.createOscillator()
        const chimeGain = ctx.createGain()

        chimeOsc.type = 'sine'
        chimeOsc.frequency.setValueAtTime(freq, start)

        chimeGain.gain.setValueAtTime(0.001, start)
        if (chimeGain.gain.linearRampToValueAtTime) {
          chimeGain.gain.linearRampToValueAtTime(peak, start + 0.005)
        }
        if (chimeGain.gain.exponentialRampToValueAtTime) {
          chimeGain.gain.exponentialRampToValueAtTime(0.001, start + dur)
        }

        chimeOsc.connect(chimeGain)
        chimeGain.connect(masterGain)

        chimeOsc.start(start)
        chimeOsc.stop(start + dur + 0.01)
        this.activeNodes.push(chimeOsc, chimeGain)
      })

      // Add high overtone sparkle for the final TIIIING
      const sparkleOsc = ctx.createOscillator()
      const sparkleGain = ctx.createGain()
      sparkleOsc.type = 'sine'
      sparkleOsc.frequency.setValueAtTime(2792, now + 0.63) // 2nd harmonic
      sparkleGain.gain.setValueAtTime(0.001, now + 0.63)
      if (sparkleGain.gain.linearRampToValueAtTime) {
        sparkleGain.gain.linearRampToValueAtTime(0.08, now + 0.64)
      }
      if (sparkleGain.gain.exponentialRampToValueAtTime) {
        sparkleGain.gain.exponentialRampToValueAtTime(0.001, now + 0.79)
      }
      sparkleOsc.connect(sparkleGain)
      sparkleGain.connect(masterGain)
      sparkleOsc.start(now + 0.63)
      sparkleOsc.stop(now + 0.8)
      this.activeNodes.push(sparkleOsc, sparkleGain)

      // =========================================================================
      // Visual Presence Amplitude Synchronization (0.0 to 0.8s)
      // =========================================================================
      const startTime = performance.now()
      const totalDurationMs = 800

      const animateAmplitude = () => {
        if (!this.isPlayingState) return
        const elapsed = performance.now() - startTime

        if (elapsed < totalDurationMs) {
          let currentAmp = 0
          if (elapsed <= 100) {
            // KLAK impact pulse
            currentAmp = 0.5 * (1 - elapsed / 100) + 0.2
          } else if (elapsed <= 420) {
            // VMMMM swelling rise
            const progress = (elapsed - 100) / 320
            currentAmp = 0.25 + progress * 0.45
          } else if (elapsed <= 520) {
            // TII #1
            currentAmp = 0.55
          } else if (elapsed <= 620) {
            // TII #2
            currentAmp = 0.62
          } else {
            // TIIIING #3 into stable listening resting wave
            const tail = (elapsed - 620) / 180
            currentAmp = 0.7 * (1 - tail * 0.7)
          }

          callbacks?.onAmplitude?.(Math.min(1, Math.max(0, currentAmp)))
          this.animationFrameId = requestAnimationFrame(animateAmplitude)
        } else {
          // Completed activation sound
          this.cleanup()
          callbacks?.onAmplitude?.(0.15) // Settles into listening baseline
          callbacks?.onEnd?.()
        }
      }

      animateAmplitude()

      // Backup safety timeout to guarantee state reset
      this.timeoutId = setTimeout(() => {
        if (this.isPlayingState) {
          this.cleanup()
          callbacks?.onEnd?.()
        }
      }, totalDurationMs + 50)
    } catch (err: any) {
      this.cleanup()
      callbacks?.onError?.(err instanceof Error ? err : new Error(String(err)))
      // Never crash caller
      callbacks?.onEnd?.()
    }
  }

  /**
   * Stop activation sound immediately (e.g. on barge-in / interrupt).
   */
  public stopActivationSound(): void {
    this.cleanup()
  }

  private cleanup(): void {
    this.isPlayingState = false

    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId)
      this.animationFrameId = null
    }

    if (this.timeoutId !== null) {
      clearTimeout(this.timeoutId)
      this.timeoutId = null
    }

    // Stop and disconnect all active nodes
    this.activeNodes.forEach((node) => {
      try {
        node.stop?.()
      } catch {}
      try {
        node.disconnect?.()
      } catch {}
    })
    this.activeNodes = []
  }
}

// Module singleton instance
export const activationSoundService = new ActivationSoundService()

/**
 * Clean functional interface
 */
export async function playActivationSound(callbacks?: ActivationSoundCallbacks): Promise<void> {
  return activationSoundService.playActivationSound(callbacks)
}

export function stopActivationSound(): void {
  activationSoundService.stopActivationSound()
}

export function isActivationSoundPlaying(): boolean {
  return activationSoundService.isPlaying
}
