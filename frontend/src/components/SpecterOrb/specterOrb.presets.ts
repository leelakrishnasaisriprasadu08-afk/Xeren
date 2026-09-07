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
    colorA: '#00f0ff',
    colorB: '#3b82f6',
    colorC: '#1e1b4b',
    specularColorA: '#67e8f9',
    specularColorB: '#93c5fd',
    rimStrength: 0.85,
    glowStrength: 1.1,
    glowFalloff: 24,
    turbulence: 0.2,
    flowSpeed: 0.06,
  },
  listening: {
    colorA: '#00f0ff',
    colorB: '#38bdf8',
    colorC: '#0284c7',
    specularColorA: '#a5f3fc',
    specularColorB: '#38bdf8',
    rimStrength: 1.15,
    glowStrength: 1.4,
    glowFalloff: 20,
    turbulence: 0.22,
    flowSpeed: 0.08,
  },
  thinking: {
    colorA: '#a855f7',
    colorB: '#6366f1',
    colorC: '#00f0ff',
    specularColorA: '#c084fc',
    specularColorB: '#818cf8',
    rimStrength: 1.05,
    glowStrength: 1.35,
    glowFalloff: 22,
    turbulence: 0.22,
    flowSpeed: 0.1,
  },
  acting: {
    colorA: '#00f0ff',
    colorB: '#10b981',
    colorC: '#2563eb',
    specularColorA: '#6ee7b7',
    specularColorB: '#38bdf8',
    rimStrength: 1.2,
    glowStrength: 1.45,
    glowFalloff: 20,
    turbulence: 0.24,
    flowSpeed: 0.12,
  },
  speaking: {
    colorA: '#38bdf8',
    colorB: '#a855f7',
    colorC: '#06b6d4',
    specularColorA: '#bae6fd',
    specularColorB: '#e9d5ff',
    rimStrength: 1.15,
    glowStrength: 1.4,
    glowFalloff: 20,
    turbulence: 0.23,
    flowSpeed: 0.09,
  },
  complete: {
    colorA: '#10b981',
    colorB: '#06b6d4',
    colorC: '#047857',
    specularColorA: '#a7f3d0',
    specularColorB: '#67e8f9',
    rimStrength: 0.95,
    glowStrength: 1.25,
    glowFalloff: 24,
    turbulence: 0.18,
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
