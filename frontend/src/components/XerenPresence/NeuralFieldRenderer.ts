import type {
  FieldParticle,
  StructuralThread,
  SignalPacket,
  RendererOptions,
} from './neuralField.types'
import type { PresenceState } from '../../types/presence'
import {
  STATE_THEMES,
  ANATOMICAL_NODES,
  PARTICLE_BUDGETS,
  type StateColorTheme,
} from './neuralField.constants'

export class NeuralFieldRenderer {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D | null = null
  private state: PresenceState = 'idle'
  private amplitude = 0
  private smoothedAmplitude = 0
  private isReducedMotion = false
  private animFrameId: number | null = null
  private isDestroyed = false

  public particles: FieldParticle[] = []
  public threads: StructuralThread[] = []
  public signals: SignalPacket[] = []
  private particleIndices: number[] = []

  // Pre-allocated transformed coordinates & rotated normals for 3D volumetric light & shadow
  private rotatedX: Float32Array = new Float32Array(0)
  private rotatedY: Float32Array = new Float32Array(0)
  private rotatedZ: Float32Array = new Float32Array(0)
  private rotatedNx: Float32Array = new Float32Array(0)
  private rotatedNy: Float32Array = new Float32Array(0)
  private rotatedNz: Float32Array = new Float32Array(0)

  private materialization = 0.0
  private time = 0
  private width = 640
  private height = 520
  private maxParticles = PARTICLE_BUDGETS.desktop

  constructor(options: RendererOptions) {
    this.canvas = options.canvas
    this.ctx = this.canvas.getContext('2d')
    this.state = options.initialState || 'idle'
    this.isReducedMotion = options.isReducedMotion || false
    this.maxParticles = options.maxParticles || PARTICLE_BUDGETS.desktop

    this.initDimensions()
    this.buildOrbAnatomy()

    if (this.isReducedMotion) {
      this.materialization = 1.0
      this.renderFrame(0)
    } else {
      this.start()
    }
  }

  public setState(nextState: PresenceState): void {
    if (this.state === nextState) return
    this.state = nextState
  }

  public setAmplitude(amp: number): void {
    this.amplitude = Math.min(1, Math.max(0, amp))
  }

  public setReducedMotion(reduced: boolean): void {
    this.isReducedMotion = reduced
    if (reduced) {
      this.stop()
      this.materialization = 1.0
      this.renderFrame(0)
    } else {
      this.start()
    }
  }

  public resize(width: number, height: number): void {
    this.width = width
    this.height = height
    this.canvas.width = width
    this.canvas.height = height
    if (this.isReducedMotion) {
      this.renderFrame(0)
    }
  }

  public start(): void {
    if (this.isDestroyed || this.animFrameId !== null) return
    let lastTimestamp = performance.now()

    const loop = (timestamp: number) => {
      if (this.isDestroyed) return
      const dt = Math.min((timestamp - lastTimestamp) / 1000, 0.08)
      lastTimestamp = timestamp

      this.update(dt)
      this.renderFrame(dt)

      this.animFrameId = requestAnimationFrame(loop)
    }

    this.animFrameId = requestAnimationFrame(loop)
  }

  public stop(): void {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId)
      this.animFrameId = null
    }
  }

  public destroy(): void {
    this.isDestroyed = true
    this.stop()
    this.particles = []
    this.threads = []
    this.signals = []
    this.particleIndices = []
    this.ctx = null
  }

  private initDimensions(): void {
    const rect = this.canvas.getBoundingClientRect()
    this.width = this.canvas.width = rect.width > 0 ? rect.width : 640
    this.height = this.canvas.height = rect.height > 0 ? rect.height : 520
  }

  // Build Iconic 3D Neural Orb Particle System (Pure Neon Dots — Zero Threads)
  private buildOrbAnatomy(): void {
    this.particles = []
    this.threads = []
    this.signals = []

    const targetNodes = ANATOMICAL_NODES.slice(0, this.maxParticles)
    const len = targetNodes.length

    this.rotatedX = new Float32Array(len)
    this.rotatedY = new Float32Array(len)
    this.rotatedZ = new Float32Array(len)
    this.rotatedNx = new Float32Array(len)
    this.rotatedNy = new Float32Array(len)
    this.rotatedNz = new Float32Array(len)

    for (let i = 0; i < len; i++) {
      const node = targetNodes[i]

      let nodeHue = 202 // Radiant electric blue
      let nodeSat = 96
      let nodeLight = 76
      let nodeSize = 1.3
      let nodeAlpha = 0.88

      if (node.orbType === 'nucleus') {
        nodeHue = 196 // White-cyan high-energy core
        nodeSat = 100
        nodeLight = 94
        nodeSize = 1.6
        nodeAlpha = 1.0
      } else if (node.orbType === 'ring') {
        nodeHue = node.ringIndex === 0 ? 190 : node.ringIndex === 1 ? 204 : 218
        nodeSat = 92
        nodeLight = 82
        nodeSize = 1.35
        nodeAlpha = 0.9
      } else if (node.orbType === 'wave') {
        nodeHue = 186 // Brilliant cyan wave particles
        nodeSat = 98
        nodeLight = 88
        nodeSize = 1.45
        nodeAlpha = 0.92
      }

      this.particles.push({
        id: node.id,
        x: node.x,
        y: node.y,
        z: node.z,
        nx: node.nx ?? 0,
        ny: node.ny ?? 0,
        nz: node.nz ?? 1,
        vx: 0,
        vy: 0,
        vz: 0,
        targetX: node.x,
        targetY: node.y,
        targetZ: node.z,
        baseX: node.x,
        baseY: node.y,
        baseZ: node.z,
        region: node.region,
        layer: node.layer,
        isStructuralNode: true,
        label: node.label,
        size: nodeSize,
        baseAlpha: nodeAlpha,
        alpha: 0,
        energy: 0.6,
        phase: (node.id * 137.5 * Math.PI) / 180,
        hue: nodeHue,
        sat: nodeSat,
        light: nodeLight,
        isBreathingThorax: node.isBreathingThorax,
      })
    }

    this.particleIndices = this.particles.map((_, idx) => idx)
  }

  // Kinetics: Audio-reactive Listening and Speaking motions
  private update(dt: number): void {
    this.time += dt
    this.smoothedAmplitude += (this.amplitude - this.smoothedAmplitude) * 0.2

    if (this.materialization < 1.0) {
      this.materialization = Math.min(1.0, this.materialization + dt * 0.95)
    }

    const theme = STATE_THEMES[this.state]
    const amp = this.smoothedAmplitude

    // 1. Organic Idle Breathing Cycle (~0.14 Hz):
    const breath = Math.sin(this.time * 0.14 * Math.PI * 2) * 0.025

    // 2. Listening Mode Motion:
    // Receptive auditory expansion + surface wave ripples undulating with incoming voice
    const isListening = this.state === 'listening'
    const listenExpansion = isListening ? 1.08 + amp * 0.35 : 1.0

    // 3. Speaking Mode Motion:
    // Dynamic vocal acoustic shockwaves & harmonic particle bursts
    const isSpeaking = this.state === 'speaking'
    const speakExpansion = isSpeaking ? 1.05 + amp * 0.55 : 1.0

    const pCount = this.particles.length
    for (let i = 0; i < pCount; i++) {
      const p = this.particles[i]
      const nodeDef = ANATOMICAL_NODES[i]
      const orbType = nodeDef?.orbType ?? 'shell'

      let scaleFactor = 1.0 + breath

      if (orbType === 'shell') {
        if (isListening) {
          // Acoustic surface ripples undulating across the spherical shell
          const ripple = Math.sin(p.baseY * 18 + this.time * 10) * Math.cos(p.baseX * 16) * (0.02 + amp * 0.28)
          scaleFactor = listenExpansion + ripple
        } else if (isSpeaking) {
          // Outward acoustic waves pulsing rhythmically with speech cadence
          const burst = Math.sin(p.baseZ * 24 - this.time * 18) * (0.03 + amp * 0.45)
          const harmonic = Math.sin(this.time * 14 + p.phase) * amp * 0.2
          scaleFactor = speakExpansion + burst + harmonic
        }
      } else if (orbType === 'nucleus') {
        // Nucleus core expands into high-energy pulse during voice activity
        if (isListening) {
          scaleFactor = 1.0 + amp * 0.3
        } else if (isSpeaking) {
          scaleFactor = 1.0 + Math.sin(this.time * 18) * 0.08 + amp * 0.65
        }
      } else if (orbType === 'wave') {
        // Radial wave particles emit outward in response to voice
        if (isListening) {
          scaleFactor = 1.1 + Math.sin(this.time * 8 + p.phase) * (0.05 + amp * 0.3)
        } else if (isSpeaking) {
          scaleFactor = 1.15 + Math.sin(this.time * 16 - p.phase) * (0.08 + amp * 0.55)
        }
      } else if (orbType === 'ring') {
        // Rings pulse in diameter with audio
        if (isListening || isSpeaking) {
          scaleFactor = 1.0 + amp * 0.18
        }
      }

      // Organic micro-shimmer
      const shimmer = Math.sin(this.time * 3.2 + p.phase) * 0.002

      const tx = p.baseX * scaleFactor + (p.nx ?? 0) * shimmer
      const ty = p.baseY * scaleFactor + (p.ny ?? 0) * shimmer
      const tz = p.baseZ * scaleFactor + (p.nz ?? 0) * shimmer

      p.x += (tx - p.x) * 0.3
      p.y += (ty - p.y) * 0.3
      p.z += (tz - p.z) * 0.3

      // Dynamic alpha and brightness surging with voice
      p.alpha = p.baseAlpha * this.materialization * theme.brightness
      if (amp > 0.02 && (isListening || isSpeaking)) {
        p.alpha = Math.min(1.0, p.alpha * (1 + amp * 0.35))
      }
    }
  }

  // Pure Volumetric Neon Dot Simulation Rendering Engine (Zero Threads / Zero Lines)
  private renderFrame(_dt: number): void {
    const ctx = this.ctx
    if (!ctx) return

    const w = this.width
    const h = this.height
    const cx = w / 2
    // Perfectly centered iconic AI Orb
    const cy = h * 0.50
    const scale = Math.min(w, h) * 0.88

    ctx.clearRect(0, 0, w, h)

    const theme = STATE_THEMES[this.state]
    const mat = this.materialization
    const amp = this.smoothedAmplitude

    // =========================================================================
    // LAYER 1: ATMOSPHERIC DEEP BLUE RADIAL AURA
    // Soft volumetric ambient glow centered on the orb
    // =========================================================================
    const orbGlowRadius = scale * (0.48 + amp * 0.12)
    if (ctx.createRadialGradient) {
      const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, orbGlowRadius)
      bgGrad.addColorStop(0, `hsla(${theme.secondaryHue}, 95%, 52%, ${0.22 * mat})`)
      bgGrad.addColorStop(0.4, `hsla(${theme.primaryHue}, 90%, 35%, ${0.1 * mat})`)
      bgGrad.addColorStop(1, 'rgba(2, 6, 23, 0)')

      ctx.fillStyle = bgGrad
      ctx.beginPath()
      ctx.arc(cx, cy, orbGlowRadius, 0, Math.PI * 2)
      ctx.fill()
    }

    // =========================================================================
    // LAYER 2: 3D VOLUMETRIC ROTATION (SPHERE YAW, PITCH & RING ROTATION)
    // Continuous majestic 3D rotation of the sphere and tilted rings
    // =========================================================================
    const sphereYaw = this.time * 0.28
    const spherePitch = Math.sin(this.time * 0.18) * 0.12

    const cosY = Math.cos(sphereYaw)
    const sinY = Math.sin(sphereYaw)
    const cosP = Math.cos(spherePitch)
    const sinP = Math.sin(spherePitch)

    const pCount = this.particles.length
    for (let i = 0; i < pCount; i++) {
      const p = this.particles[i]
      const nodeDef = ANATOMICAL_NODES[i]
      const orbType = nodeDef?.orbType ?? 'shell'

      let curX = p.x
      let curY = p.y
      let curZ = p.z
      let curNx = p.nx ?? 0
      let curNy = p.ny ?? 0
      let curNz = p.nz ?? 1

      // Orbital rings rotate at independent speeds
      if (orbType === 'ring') {
        const ringIdx = nodeDef?.ringIndex ?? 0
        const ringSpin = ringIdx === 0 ? this.time * 0.45 : ringIdx === 1 ? -this.time * 0.35 : this.time * 0.25
        const cosR = Math.cos(ringSpin)
        const sinR = Math.sin(ringSpin)
        const rx = curX * cosR - curZ * sinR
        const rz = curX * sinR + curZ * cosR
        curX = rx
        curZ = rz
      }

      // Rotate sphere
      const x1 = curX * cosY - curZ * sinY
      const z1 = curX * sinY + curZ * cosY
      const y1 = curY * cosP - z1 * sinP
      const z2 = curY * sinP + z1 * cosP

      this.rotatedX[i] = x1
      this.rotatedY[i] = y1
      this.rotatedZ[i] = z2

      // Rotate normals
      const nx1 = curNx * cosY - curNz * sinY
      const nz1 = curNx * sinY + curNz * cosY
      const ny1 = curNy * cosP - nz1 * sinP
      const nz2 = ny0toP(curNy, sinP, nz1, cosP)

      this.rotatedNx[i] = nx1
      this.rotatedNy[i] = ny1
      this.rotatedNz[i] = nz2
    }

    // Sort particle indices by rotated Z-depth (back to front) for accurate 3D occlusion
    this.particleIndices.sort((a, b) => this.rotatedZ[a] - this.rotatedZ[b])

    // =========================================================================
    // LAYER 3: CENTRAL RADIANT XEREN ORB NUCLEUS (Inner Core & Containment Rings)
    // =========================================================================
    const coreRadius = scale * (0.13 + amp * 0.05)
    this.drawOrbNucleus(ctx, cx, cy, coreRadius, theme)

    // =========================================================================
    // LAYER 4: PURE 3D NEON DOT POINT CLOUD
    // Multi-stage photon emission: Outer Halo -> Mid Cyan Body -> White-Hot Center
    // =========================================================================
    const fov = 1.95
    for (let i = 0; i < pCount; i++) {
      const idx = this.particleIndices[i]
      const p = this.particles[idx]
      const rx = this.rotatedX[idx]
      const ry = this.rotatedY[idx]
      const rz = this.rotatedZ[idx]
      const rnz = this.rotatedNz[idx]

      const perspective = fov / (fov - rz * 0.55)
      const px = cx + rx * scale * perspective
      const py = cy + ry * scale * perspective
      const radius = Math.max(0.65, p.size * perspective)

      // Depth lighting: frontal points are brighter, back points softer
      const depthFactor = Math.min(1.0, Math.max(0.2, (rz + 0.35) / 0.7))
      const fresnel = Math.pow(1 - Math.max(0, rnz), 2) * 0.35
      const effectiveAlpha = p.alpha * (0.35 + depthFactor * 0.65 + fresnel)

      // 1. Tight, subtle outer neon halo bloom
      ctx.fillStyle = `hsla(${p.hue}, 100%, 72%, ${effectiveAlpha * 0.28})`
      ctx.beginPath()
      ctx.arc(px, py, radius * 1.5, 0, Math.PI * 2)
      ctx.fill()

      // 2. Mid intense electric cyan/blue disc
      ctx.fillStyle = `hsla(${p.hue}, 100%, 82%, ${effectiveAlpha * 0.9})`
      ctx.beginPath()
      ctx.arc(px, py, radius * 0.95, 0, Math.PI * 2)
      ctx.fill()

      // 3. Pinpoint luminous white-hot photon center
      ctx.fillStyle = `rgba(255, 255, 255, ${effectiveAlpha * 0.98})`
      ctx.beginPath()
      ctx.arc(px, py, radius * 0.5, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  // Draw Radiant Embedded Orb Nucleus & Containment Rings
  private drawOrbNucleus(
    ctx: CanvasRenderingContext2D,
    coreX: number,
    coreY: number,
    radius: number,
    theme: StateColorTheme
  ): void {
    const mat = this.materialization
    if (mat <= 0) return

    const corePulse = 1 + Math.sin(this.time * 2.8) * 0.04 + this.smoothedAmplitude * 0.25

    // 1. High-energy volumetric photon bloom
    const emFieldRadius = radius * 2.2 * corePulse
    if (ctx.createRadialGradient) {
      const emGrad = ctx.createRadialGradient(coreX, coreY, 0, coreX, coreY, emFieldRadius)
      emGrad.addColorStop(0, `rgba(255, 255, 255, ${0.9 * mat})`)
      emGrad.addColorStop(0.25, `hsla(${theme.primaryHue}, 100%, 75%, ${0.7 * mat})`)
      emGrad.addColorStop(0.6, `hsla(${theme.secondaryHue}, 95%, 60%, ${0.3 * mat})`)
      emGrad.addColorStop(1, 'rgba(0, 210, 255, 0)')

      ctx.fillStyle = emGrad
      ctx.beginPath()
      ctx.arc(coreX, coreY, emFieldRadius, 0, Math.PI * 2)
      ctx.fill()
    }

    // 2. Rotating crystalline containment rings
    if (ctx.save && ctx.restore) {
      ctx.save()
      ctx.translate(coreX, coreY)

      ctx.rotate(-this.time * 0.4)
      ctx.strokeStyle = `hsla(${theme.secondaryHue}, 90%, 75%, ${0.42 * mat})`
      ctx.lineWidth = 1.2
      this.drawHexagon(ctx, 0, 0, radius * 1.35 * corePulse)
      ctx.stroke()

      ctx.rotate(this.time * 0.8)
      ctx.strokeStyle = `hsla(${theme.primaryHue}, 100%, 80%, ${0.55 * mat})`
      ctx.lineWidth = 1.3
      if (ctx.setLineDash) ctx.setLineDash([10, 6, 4, 6])
      ctx.beginPath()
      ctx.arc(0, 0, radius * 1.05 * corePulse, 0, Math.PI * 2)
      ctx.stroke()
      if (ctx.setLineDash) ctx.setLineDash([])

      ctx.restore()
    }

    // 3. High-energy nucleus with white-hot radial gradient
    if (ctx.createRadialGradient) {
      const nucGrad = ctx.createRadialGradient(
        coreX - radius * 0.15,
        coreY - radius * 0.15,
        0,
        coreX,
        coreY,
        radius * 0.8
      )
      nucGrad.addColorStop(0, `hsla(0, 0%, 100%, ${0.98 * mat})`)
      nucGrad.addColorStop(0.35, `hsla(${theme.primaryHue}, 100%, 74%, ${0.88 * mat})`)
      nucGrad.addColorStop(0.75, `hsla(${theme.secondaryHue}, 90%, 55%, ${0.75 * mat})`)
      nucGrad.addColorStop(1, `hsla(225, 95%, 10%, ${0.85 * mat})`)

      ctx.fillStyle = nucGrad
      ctx.beginPath()
      ctx.arc(coreX, coreY, radius * 0.8 * corePulse, 0, Math.PI * 2)
      ctx.fill()
    }

    // 4. Embedded Xeren Chevron 'X' Emblem
    const xSize = radius * 0.38 * corePulse
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 2.4
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    ctx.beginPath()
    ctx.moveTo(coreX - xSize * 0.8, coreY - xSize)
    ctx.lineTo(coreX - xSize * 0.15, coreY)
    ctx.lineTo(coreX - xSize * 0.8, coreY + xSize)

    ctx.moveTo(coreX + xSize * 0.8, coreY - xSize)
    ctx.lineTo(coreX + xSize * 0.15, coreY)
    ctx.lineTo(coreX + xSize * 0.8, coreY + xSize)
    ctx.stroke()

    // Central light nucleus dot
    ctx.fillStyle = '#ffffff'
    ctx.beginPath()
    ctx.arc(coreX, coreY, 2.5, 0, Math.PI * 2)
    ctx.fill()
  }

  private drawHexagon(ctx: CanvasRenderingContext2D, x: number, y: number, r: number): void {
    ctx.beginPath()
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i
      const hx = x + r * Math.cos(angle)
      const hy = y + r * Math.sin(angle)
      if (i === 0) ctx.moveTo(hx, hy)
      else ctx.lineTo(hx, hy)
    }
    ctx.closePath()
  }
}

function ny0toP(ny: number, sinP: number, nz1: number, cosP: number): number {
  return ny * sinP + nz1 * cosP
}
