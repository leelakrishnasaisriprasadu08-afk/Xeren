import React, { useRef, useEffect } from 'react'
import type { PresenceState } from '../../types/presence'
import { useAdaptivePerformance } from '../../hooks/useAdaptivePerformance'
import './AtmosphericBackground.css'

interface AtmosphericBackgroundProps {
  state?: PresenceState
  isReducedMotion?: boolean
}

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  baseAlpha: number
  alpha: number
  hue: number
}

export const AtmosphericBackground: React.FC<AtmosphericBackgroundProps> = ({
  state = 'idle',
  isReducedMotion = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const animFrameIdRef = useRef<number | null>(null)
  const particlesRef = useRef<Particle[]>([])
  const { maxBackgroundParticles } = useAdaptivePerformance(isReducedMotion)

  // Initialize and animate canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)

    const handleResize = () => {
      if (!canvas) return
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }

    window.addEventListener('resize', handleResize)

    // Generate sparse particles (25-35 on desktop, fewer on mobile/tablet)
    const particleCount = maxBackgroundParticles
    const particles: Particle[] = []

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.22,
        radius: Math.random() * 1.5 + 0.8,
        baseAlpha: Math.random() * 0.28 + 0.12,
        alpha: Math.random() * 0.28 + 0.12,
        hue: Math.random() > 0.6 ? 190 : 270, // cyan or soft violet
      })
    }
    particlesRef.current = particles

    // If reduced motion is requested, render once and don't loop
    if (isReducedMotion || particleCount === 0) {
      ctx.clearRect(0, 0, width, height)
      particles.forEach((p) => {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `hsla(${p.hue}, 80%, 75%, ${p.baseAlpha * 0.5})`
        ctx.fill()
      })
      return () => {
        window.removeEventListener('resize', handleResize)
      }
    }

    let lastTime = performance.now()

    const render = (time: number) => {
      const dt = Math.min((time - lastTime) / 1000, 0.1)
      lastTime = time

      ctx.clearRect(0, 0, width, height)

      // State-specific particle flow modifiers
      const centerX = width / 2
      const centerY = height * 0.35 // Position of presence

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]

        // State vector influences
        if (state === 'listening') {
          // Subtle attraction toward presence center
          const dx = centerX - p.x
          const dy = centerY - p.y
          const dist = Math.hypot(dx, dy)
          if (dist > 50) {
            p.vx += (dx / dist) * 0.05 * dt
            p.vy += (dy / dist) * 0.05 * dt
          }
        } else if (state === 'acting') {
          // Gentle directional outward/downward drift
          p.vy += 0.04 * dt
        } else if (state === 'thinking') {
          // Orbital micro-drift
          const dx = centerX - p.x
          const dy = centerY - p.y
          p.vx += (-dy * 0.00008)
          p.vy += (dx * 0.00008)
        }

        // Apply velocity with damping to avoid runaway acceleration
        p.vx *= 0.985
        p.vy *= 0.985

        p.x += p.vx
        p.y += p.vy

        // Wrap around screen edges
        if (p.x < -10) p.x = width + 10
        if (p.x > width + 10) p.x = -10
        if (p.y < -10) p.y = height + 10
        if (p.y > height + 10) p.y = -10

        // Draw particle
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `hsla(${p.hue}, 80%, 75%, ${p.alpha})`
        ctx.fill()
      }

      // Draw faint connections between adjacent particles (< 85px)
      ctx.lineWidth = 0.5
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const p1 = particles[i]
          const p2 = particles[j]
          const dx = p1.x - p2.x
          const dy = p1.y - p2.y
          const dist = Math.hypot(dx, dy)

          if (dist < 85) {
            const lineAlpha = (1 - dist / 85) * 0.065
            ctx.strokeStyle = `rgba(0, 240, 255, ${lineAlpha})`
            ctx.beginPath()
            ctx.moveTo(p1.x, p1.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.stroke()
          }
        }
      }

      animFrameIdRef.current = requestAnimationFrame(render)
    }

    animFrameIdRef.current = requestAnimationFrame(render)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (animFrameIdRef.current !== null) {
        cancelAnimationFrame(animFrameIdRef.current)
      }
    }
  }, [state, isReducedMotion, maxBackgroundParticles])

  return (
    <div
      className={`atmospheric-background-container state-${state} ${
        isReducedMotion ? 'reduced-motion' : ''
      }`}
      aria-hidden="true"
      data-testid="atmospheric-background"
    >
      {/* Distant soft radial light fields */}
      <div className="atmospheric-radial-glow glow-center-top" />
      <div className="atmospheric-radial-glow glow-bottom-left" />
      <div className="atmospheric-radial-glow glow-bottom-right" />

      {/* Faint computational grid */}
      <div className="atmospheric-grid-layer" />

      {/* Sparse dynamic particles & faint constellation lines */}
      <canvas ref={canvasRef} className="atmospheric-canvas" />
    </div>
  )
}
