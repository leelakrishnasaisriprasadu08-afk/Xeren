import type { PresenceState, AnatomicalLayer, AnatomicalRegion } from './neuralField.types'

export interface StateColorTheme {
  primaryHue: number
  secondaryHue: number
  accentHue: number
  coreGlow: string
  brightness: number
}

export const STATE_THEMES: Record<PresenceState, StateColorTheme> = {
  idle: {
    primaryHue: 202, // Vibrant Electric Cobalt Blue
    secondaryHue: 190, // Bright Cyan
    accentHue: 215, // Deep Azure
    coreGlow: 'rgba(0, 180, 255, 0.65)',
    brightness: 1.05,
  },
  listening: {
    primaryHue: 196, // High-voltage Cyan-Blue
    secondaryHue: 208, // Neon Electric Blue
    accentHue: 185, // Electric Cyan
    coreGlow: 'rgba(0, 220, 255, 0.75)',
    brightness: 1.28,
  },
  thinking: {
    primaryHue: 216, // Deep Electric Sapphire
    secondaryHue: 230, // Luminous Indigo-Blue
    accentHue: 195, // Bright Cyan
    coreGlow: 'rgba(30, 144, 255, 0.8)',
    brightness: 1.35,
  },
  acting: {
    primaryHue: 190, // High-voltage Cyan
    secondaryHue: 205, // Cobalt Blue
    accentHue: 175, // Teal-Cyan
    coreGlow: 'rgba(0, 245, 255, 0.75)',
    brightness: 1.3,
  },
  speaking: {
    primaryHue: 205, // Radiant Sky-Blue
    secondaryHue: 220, // Ultramarine Blue
    accentHue: 192, // Bright Cyan
    coreGlow: 'rgba(56, 189, 248, 0.75)',
    brightness: 1.25,
  },
  complete: {
    primaryHue: 180, // Crystalline Aqua-Cyan
    secondaryHue: 200, // Electric Blue
    accentHue: 165, // Bright Turquoise
    coreGlow: 'rgba(0, 255, 215, 0.8)',
    brightness: 1.35,
  },
  error: {
    primaryHue: 358, // Crimson (restrained warning)
    secondaryHue: 210, // Electric Blue
    accentHue: 15, // Amber
    coreGlow: 'rgba(239, 68, 68, 0.7)',
    brightness: 1.15,
  },
  paused: {
    primaryHue: 210, // Subdued Slate Blue
    secondaryHue: 218, // Steel Blue
    accentHue: 205, // Dim Cyan
    coreGlow: 'rgba(100, 149, 237, 0.35)',
    brightness: 0.65,
  },
}

export interface AnatomicalNodeDef {
  id: number
  label: string
  x: number
  y: number
  z: number
  nx?: number
  ny?: number
  nz?: number
  region: AnatomicalRegion
  layer: AnatomicalLayer
  isBreathingThorax?: boolean
  orbType?: 'shell' | 'ring' | 'nucleus' | 'wave'
  ringIndex?: number
  baseRadius?: number
}

// ICONIC 3D NEURAL ORB INTERFACE (PURE NEON PARTICLES — ZERO THREADS)
// A recognizable, premium living AI Orb with audio-reactive listening & speaking kinetic motions
function createNeuralOrbPointCloud(): AnatomicalNodeDef[] {
  const nodes: AnatomicalNodeDef[] = []
  let nextId = 0

  const phi = (1 + Math.sqrt(5)) / 2 // Golden ratio
  const orbRadius = 0.28

  // 1. FIBONACCI SPHERICAL SURFACE SHELL (950 dots)
  // Uniform mathematical spherical distribution
  const numShellDots = 950
  for (let i = 0; i < numShellDots; i++) {
    const yNorm = 1 - (i / (numShellDots - 1)) * 2 // 1 to -1
    const radiusAtY = Math.sqrt(Math.max(0, 1 - yNorm * yNorm))
    const theta = (2 * Math.PI * i) / phi

    const x = Math.cos(theta) * radiusAtY * orbRadius
    const z = Math.sin(theta) * radiusAtY * orbRadius
    const y = yNorm * orbRadius

    const nx = x / orbRadius
    const ny = y / orbRadius
    const nz = z / orbRadius

    nodes.push({
      id: nextId++,
      label: `Orb Shell ${nextId}`,
      x,
      y,
      z,
      nx,
      ny,
      nz,
      region: 'core',
      layer: 'surface',
      isBreathingThorax: true,
      orbType: 'shell',
      baseRadius: orbRadius,
    })
  }

  // 2. ORBITAL CRYSTALLINE RINGS (3 Independent Tilted Particle Bands ~ 480 dots)
  // Ring 0: Equatorial ring
  const r0 = orbRadius * 1.28
  for (let d = 0; d < 160; d++) {
    const ang = (d / 160.0) * Math.PI * 2
    const x = Math.cos(ang) * r0
    const y = Math.sin(ang) * 0.015
    const z = Math.sin(ang) * r0
    nodes.push({
      id: nextId++,
      label: `Equatorial Ring ${nextId}`,
      x,
      y,
      z,
      nx: x / r0,
      ny: 0,
      nz: z / r0,
      region: 'core',
      layer: 'skeletal',
      orbType: 'ring',
      ringIndex: 0,
      baseRadius: r0,
    })
  }

  // Ring 1: Tilted orbital ring (+35 degrees)
  const r1 = orbRadius * 1.38
  const tilt1 = (35 * Math.PI) / 180
  for (let d = 0; d < 160; d++) {
    const ang = (d / 160.0) * Math.PI * 2
    const rx = Math.cos(ang) * r1
    const rz = Math.sin(ang) * r1
    const x = rx
    const y = -rz * Math.sin(tilt1)
    const z = rz * Math.cos(tilt1)
    nodes.push({
      id: nextId++,
      label: `Orbital Ring 1 ${nextId}`,
      x,
      y,
      z,
      nx: x / r1,
      ny: y / r1,
      nz: z / r1,
      region: 'core',
      layer: 'skeletal',
      orbType: 'ring',
      ringIndex: 1,
      baseRadius: r1,
    })
  }

  // Ring 2: Counter-tilted orbital ring (-45 degrees)
  const r2 = orbRadius * 1.48
  const tilt2 = (-45 * Math.PI) / 180
  for (let d = 0; d < 160; d++) {
    const ang = (d / 160.0) * Math.PI * 2
    const rx = Math.cos(ang) * r2
    const rz = Math.sin(ang) * r2
    const x = rx * Math.cos(tilt2)
    const y = rx * Math.sin(tilt2)
    const z = rz
    nodes.push({
      id: nextId++,
      label: `Orbital Ring 2 ${nextId}`,
      x,
      y,
      z,
      nx: x / r2,
      ny: y / r2,
      nz: z / r2,
      region: 'core',
      layer: 'skeletal',
      orbType: 'ring',
      ringIndex: 2,
      baseRadius: r2,
    })
  }

  // 3. INNER RADIANT NUCLEUS CORE (220 dots)
  const numNucleus = 220
  for (let i = 0; i < numNucleus; i++) {
    const yNorm = 1 - (i / (numNucleus - 1)) * 2
    const radiusAtY = Math.sqrt(Math.max(0, 1 - yNorm * yNorm))
    const theta = (2 * Math.PI * i) / phi
    const rNuc = 0.12 * Math.pow((i + 1) / numNucleus, 0.5)

    const x = Math.cos(theta) * radiusAtY * rNuc
    const z = Math.sin(theta) * radiusAtY * rNuc
    const y = yNorm * rNuc

    nodes.push({
      id: nextId++,
      label: `Nucleus Core ${nextId}`,
      x,
      y,
      z,
      nx: 0,
      ny: 0,
      nz: 1,
      region: 'core',
      layer: 'core',
      orbType: 'nucleus',
      baseRadius: rNuc,
    })
  }

  // 4. ACOUSTIC WAVE / RADIAL PULSE EMITTERS (150 dots)
  for (let i = 0; i < 150; i++) {
    const theta = (i * 137.5 * Math.PI) / 180.0
    const pitch = Math.sin(i * 2.3) * Math.PI * 0.4
    const r = 0.22 + (i / 150.0) * 0.14
    const x = r * Math.cos(theta) * Math.cos(pitch)
    const y = r * Math.sin(pitch)
    const z = r * Math.sin(theta) * Math.cos(pitch)
    nodes.push({
      id: nextId++,
      label: `Acoustic Emitter ${nextId}`,
      x,
      y,
      z,
      nx: x / r,
      ny: y / r,
      nz: z / r,
      region: 'core',
      layer: 'muscular',
      orbType: 'wave',
      baseRadius: r,
    })
  }

  return nodes
}

export const ANATOMICAL_NODES: AnatomicalNodeDef[] = createNeuralOrbPointCloud()

// ZERO THREADS (Pure neon dot simulation matching user requirement)
export const ANATOMICAL_THREADS: [number, number][] = []

export const PARTICLE_BUDGETS = {
  desktop: 1800,
  tablet: 1200,
  mobile: 750,
  high: 1800,
  medium: 1200,
  low: 750,
}
