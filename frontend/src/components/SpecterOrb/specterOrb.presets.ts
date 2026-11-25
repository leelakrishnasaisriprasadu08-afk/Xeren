import type { PresenceState } from '../../types/presence'

export interface XerenSpecterTheme {
  colorA: string
  colorB: string
  colorC: string
  specularColorA: string
  specularColorB: string
  rimStrength: number
  glowStrength: number
  glowFalloff: number
  turbulence: number
  flowSpeed: number
}

export const XEREN_SPECTER_THEMES: Record<PresenceState, XerenSpecterTheme> = {
  idle: {
    colorA: '#ffffff',
    colorB: '#e2e8f0',
    colorC: '#10b981',
    specularColorA: '#ffffff',
    specularColorB: '#6ee7b7',
    rimStrength: 1.1,
    glowStrength: 1.35,
    glowFalloff: 22,
    turbulence: 0.18,
    flowSpeed: 0.06,
  },
  listening: {
    colorA: '#ffffff',
    colorB: '#dcfce7',
    colorC: '#10b981',
    specularColorA: '#ffffff',
    specularColorB: '#34d399',
    rimStrength: 1.25,
    glowStrength: 1.5,
    glowFalloff: 18,
    turbulence: 0.22,
    flowSpeed: 0.08,
  },
  thinking: {
    colorA: '#ffffff',
    colorB: '#e0e7ff',
    colorC: '#059669',
    specularColorA: '#ffffff',
    specularColorB: '#34d399',
    rimStrength: 1.2,
    glowStrength: 1.5,
    glowFalloff: 20,
    turbulence: 0.22,
    flowSpeed: 0.1,
  },
  acting: {
    colorA: '#ffffff',
    colorB: '#e0f2fe',
    colorC: '#10b981',
    specularColorA: '#ffffff',
    specularColorB: '#38bdf8',
    rimStrength: 1.25,
    glowStrength: 1.55,
    glowFalloff: 18,
    turbulence: 0.24,
    flowSpeed: 0.12,
  },
  speaking: {
    colorA: '#ffffff',
    colorB: '#ecfdf5',
    colorC: '#059669',
    specularColorA: '#ffffff',
    specularColorB: '#10b981',
    rimStrength: 1.3,
    glowStrength: 1.6,
    glowFalloff: 18,
    turbulence: 0.22,
    flowSpeed: 0.09,
  },
  complete: {
    colorA: '#ffffff',
    colorB: '#f0fdf4',
    colorC: '#10b981',
    specularColorA: '#ffffff',
    specularColorB: '#6ee7b7',
    rimStrength: 1.05,
    glowStrength: 1.35,
    glowFalloff: 22,
    turbulence: 0.16,
    flowSpeed: 0.07,
  },
  error: {
    colorA: '#ef4444',
    colorB: '#f59e0b',
    colorC: '#7f1d1d',
    specularColorA: '#fca5a5',
    specularColorB: '#fcd34d',
    rimStrength: 1.25,
    glowStrength: 1.45,
    glowFalloff: 18,
    turbulence: 0.26,
    flowSpeed: 0.14,
  },
  paused: {
    colorA: '#64748b',
    colorB: '#475569',
    colorC: '#0f172a',
    specularColorA: '#94a3b8',
    specularColorB: '#64748b',
    rimStrength: 0.4,
    glowStrength: 0.6,
    glowFalloff: 34,
    turbulence: 0.12,
    flowSpeed: 0.03,
  },
}
