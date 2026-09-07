import type { PresenceState } from '../../types/presence'
export type { PresenceState }

export type AnatomicalRegion =
  | 'head'
  | 'face'
  | 'eyes'
  | 'mouth'
  | 'neck'
  | 'spine'
  | 'shoulders'
  | 'arms'
  | 'chest'
  | 'ribs'
  | 'core'
  | 'waist'

export type AnatomicalLayer = 'skeletal' | 'muscular' | 'surface' | 'core'

export interface FieldParticle {
  id: number
  x: number
  y: number
  z: number
  nx?: number
  ny?: number
  nz?: number
  vx: number
  vy: number
  vz: number
  targetX: number
  targetY: number
  targetZ: number
  baseX: number
  baseY: number
  baseZ: number
  region: AnatomicalRegion
  layer?: AnatomicalLayer
  isStructuralNode: boolean
  label?: string
  size: number
  baseAlpha: number
  alpha: number
  energy: number
  phase: number
  hue: number
  sat: number
  light: number
  isBreathingThorax?: boolean
  flowThreadIdx?: number
  flowT?: number
  flowSpeed?: number
}

export interface StructuralThread {
  id: string
  nodeA: number // Particle index A
  nodeB: number // Particle index B
  baseAlpha: number
  alpha: number
  width: number
  layer?: AnatomicalLayer
}

export interface SignalPacket {
  id: number
  nodeA: number
  nodeB: number
  progress: number
  speed: number
  intensity: number
  hue: number
}

export interface RendererOptions {
  canvas: HTMLCanvasElement
  initialState?: PresenceState
  isReducedMotion?: boolean
  maxParticles?: number
}
