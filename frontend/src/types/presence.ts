/**
 * States of the animated Xeren AI Presence.
 */
export type PresenceState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'acting'
  | 'speaking'
  | 'paused'
  | 'error'
  | 'complete'

export interface PresenceConfig {
  state: PresenceState
  amplitude?: number // 0.0 to 1.0 (microphone or speaker amplitude)
  reducedMotion?: boolean
  interactive?: boolean
  label?: string
}
