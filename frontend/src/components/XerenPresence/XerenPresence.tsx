import React, { useEffect, useRef } from 'react'
import type { PresenceState } from '../../types/presence'
import { NeuralFieldRenderer } from './NeuralFieldRenderer'
import { useAdaptivePerformance } from '../../hooks/useAdaptivePerformance'
import { PARTICLE_BUDGETS } from './neuralField.constants'
import { XerenSpecterOrb } from '../SpecterOrb/XerenSpecterOrb'
import './XerenPresence.css'

export interface XerenPresenceProps {
  state: PresenceState
  amplitude?: number
  isReducedMotion?: boolean
  mode?: 'neural-field' | 'specter-orb'
  onClick?: () => void
}

export const XerenPresence: React.FC<XerenPresenceProps> = ({
  state,
  amplitude = 0,
  isReducedMotion = false,
  mode = 'specter-orb',
  onClick,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const rendererRef = useRef<NeuralFieldRenderer | null>(null)
  const { tier } = useAdaptivePerformance(isReducedMotion)

  const stateLabels: Record<PresenceState, string> = {
    idle: 'Xeren is present',
    listening: 'Listening...',
    thinking: 'Thinking...',
    acting: 'Executing task...',
    speaking: 'Speaking...',
    paused: 'Paused',
    error: 'Attention required',
    complete: 'Ready',
  }

  // Initialize and manage NeuralFieldRenderer lifecycle
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const particleCount =
      tier === 'low'
        ? PARTICLE_BUDGETS.low
        : tier === 'medium'
        ? PARTICLE_BUDGETS.medium
        : PARTICLE_BUDGETS.high

    const renderer = new NeuralFieldRenderer({
      canvas,
      initialState: state,
      isReducedMotion,
      maxParticles: particleCount,
    })
    rendererRef.current = renderer

    // Handle container resize gracefully
    const handleResize = () => {
      if (!canvas || !rendererRef.current) return
      const rect = canvas.getBoundingClientRect()
      const w = Math.floor(rect.width || 480)
      const h = Math.floor(rect.height || 480)
      rendererRef.current.resize(w, h)
    }

    let resizeObserver: ResizeObserver | null = null
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => handleResize())
      resizeObserver.observe(canvas)
    } else {
      window.addEventListener('resize', handleResize)
    }

    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect()
      } else {
        window.removeEventListener('resize', handleResize)
      }
      renderer.destroy()
      rendererRef.current = null
    }
  }, [isReducedMotion, tier])

  // Sync state transitions to renderer
  useEffect(() => {
    if (rendererRef.current) {
      rendererRef.current.setState(state)
    }
  }, [state])

  // Sync voice/audio amplitude to renderer
  useEffect(() => {
    if (rendererRef.current) {
      rendererRef.current.setAmplitude(amplitude)
    }
  }, [amplitude])

  // Sync reduced motion changes
  useEffect(() => {
    if (rendererRef.current) {
      rendererRef.current.setReducedMotion(isReducedMotion)
    }
  }, [isReducedMotion])

  return (
    <div
      className={`xeren-presence-container state-${state} ${
        isReducedMotion ? 'reduced-motion' : ''
      }`}
      role="status"
      aria-label={`AI Presence: ${stateLabels[state]}`}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      data-testid="xeren-presence"
    >
      {/* Volumetric Neural Intelligence Stage */}
      <div className="xeren-presence-stage">
        {/* Ambient atmospheric backdrop aura */}
        <div className="presence-volumetric-glow" aria-hidden="true" />

        {mode === 'specter-orb' ? (
          <div className="presence-specter-wrap" data-testid="presence-specter-orb">
            <XerenSpecterOrb
              state={state}
              amplitude={amplitude}
              isReducedMotion={isReducedMotion}
              width="100%"
              height="100%"
            />
          </div>
        ) : (
          /* Dynamic 3D Neural Field Canvas */
          <canvas
            ref={canvasRef}
            className="presence-neural-canvas"
            aria-hidden="true"
          />
        )}
      </div>

      {/* Dynamic Status Text Label */}
      <div className="presence-state-label" data-testid="presence-state-label">
        <span className="presence-state-dot" />
        <span>{stateLabels[state]}</span>
      </div>
    </div>
  )
}
