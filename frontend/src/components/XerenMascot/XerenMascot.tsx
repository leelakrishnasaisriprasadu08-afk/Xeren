import React, { useState, useEffect, useRef } from 'react'
import type { PresenceState } from '../../types/presence'
import './XerenMascot.css'

export interface XerenMascotProps {
  state: PresenceState
  amplitude?: number
  isReducedMotion?: boolean
  width?: string | number
  height?: string | number
}

export const XerenMascot: React.FC<XerenMascotProps> = ({
  state,
  amplitude = 0,
  isReducedMotion = false,
  width = '100%',
  height = '100%',
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [tilt, setTilt] = useState({ x: 0, y: 0 })

  const isSpeaking = state === 'speaking' || amplitude > 0.08
  const isThinking = state === 'thinking'
  const isActing = state === 'acting'
  const isListening = state === 'listening'
  const isWorking = isSpeaking || isThinking || isActing || isListening

  // Subtle 3D interactive tracking towards pointer
  useEffect(() => {
    if (isReducedMotion) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      const dx = (e.clientX - centerX) / (window.innerWidth / 2)
      const dy = (e.clientY - centerY) / (window.innerHeight / 2)
      setTilt({
        x: Math.max(-12, Math.min(12, dx * 14)),
        y: Math.max(-10, Math.min(10, dy * 12)),
      })
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [isReducedMotion])

  // Eye gaze displacement based on state & 3D tilt
  const eyeShiftX = isThinking ? -6 : tilt.x * 0.4
  const eyeShiftY = isThinking ? -8 : tilt.y * 0.4

  return (
    <div
      ref={containerRef}
      className={`xeren-3d-ball-container state-${state} ${
        isWorking ? 'stage-come-forward' : 'stage-go-back'
      } ${isReducedMotion ? 'reduced-motion' : ''}`}
      data-testid="xeren-mascot"
      style={{ width, height }}
    >
      {/* 3D Dynamic Floating Sphere */}
      <div
        className="ball-3d-sphere-wrap"
        style={{
          transform: isReducedMotion
            ? 'none'
            : `rotateY(${tilt.x}deg) rotateX(${-tilt.y}deg)`,
        }}
      >
        <svg
          viewBox="0 0 280 280"
          className="ball-3d-svg"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <defs>
            {/* Deep Obsidian-Black Spherical Radial Shading */}
            <radialGradient id="blackSphereGrad" cx="36%" cy="30%" r="72%">
              <stop offset="0%" stopColor="#1e293b" />
              <stop offset="25%" stopColor="#0f172a" />
              <stop offset="60%" stopColor="#05080a" />
              <stop offset="90%" stopColor="#020406" />
              <stop offset="100%" stopColor="#000000" />
            </radialGradient>

            {/* Glowing Emerald Rim Light */}
            <radialGradient id="emeraldRimLight" cx="50%" cy="50%" r="50%">
              <stop offset="78%" stopColor="transparent" stopOpacity="0" />
              <stop offset="88%" stopColor="#059669" stopOpacity="0.4" />
              <stop offset="94%" stopColor="#10b981" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#6ee7b7" stopOpacity="0.95" />
            </radialGradient>

            {/* Specular White Gloss Gradient */}
            <linearGradient id="glossGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.85" />
              <stop offset="40%" stopColor="#ffffff" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
            </linearGradient>

            {/* Eye Sclera Gradient */}
            <radialGradient id="eyeScleraGrad" cx="40%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="85%" stopColor="#f0fdf4" />
              <stop offset="100%" stopColor="#d1fae5" />
            </radialGradient>

            {/* Pupil Emerald Iris Gradient */}
            <radialGradient id="pupilIrisGrad" cx="40%" cy="40%" r="60%">
              <stop offset="0%" stopColor="#34d399" />
              <stop offset="50%" stopColor="#059669" />
              <stop offset="85%" stopColor="#022c22" />
              <stop offset="100%" stopColor="#000000" />
            </radialGradient>

            {/* Atmospheric Emerald Volumetric Glow Filter */}
            <filter id="emeraldAura" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur" />
              <feColorMatrix
                in="blur"
                type="matrix"
                values="
                  0 0 0 0 0.06
                  0 0 0 0 0.72
                  0 0 0 0 0.50
                  0 0 0 0 0.7 0
                "
                result="glow"
              />
              <feMerge>
                <feMergeNode in="glow" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Volumetric Emerald Backlight Aura */}
          <circle
            cx="140"
            cy="135"
            r="105"
            fill="rgba(16, 185, 129, 0.22)"
            className="ball-ambient-aura"
          />

          {/* ══════════════ 1. THE 3D BLACK BALL BODY ══════════════ */}
          <g className="mascot-body-group">
            {/* Core Obsidian Black Sphere */}
            <circle
              cx="140"
              cy="135"
              r="95"
              fill="url(#blackSphereGrad)"
              filter="url(#emeraldAura)"
            />

            {/* Emerald Curved Rim Reflection */}
            <circle
              cx="140"
              cy="135"
              r="95"
              fill="url(#emeraldRimLight)"
            />

            {/* Upper Glass Specular Curve Highlight */}
            <path
              d="M 90 85 Q 140 55 195 80 Q 150 65 100 82 Z"
              fill="url(#glossGrad)"
            />

            {/* Brilliant Primary Specular Hotspot */}
            <ellipse
              cx="178"
              cy="86"
              rx="18"
              ry="11"
              transform="rotate(-26 178 86)"
              fill="#ffffff"
              opacity="0.9"
            />

            {/* Secondary Soft Ambient Bounce Light */}
            <ellipse
              cx="105"
              cy="195"
              rx="24"
              ry="7"
              transform="rotate(25 105 195)"
              fill="#34d399"
              opacity="0.25"
            />
          </g>

          {/* ══════════════ 2. 3D ANIMATED EYES (WITH PARALLAX SHIFT) ══════════════ */}
          <g
            className="mascot-eyes-container"
            style={{
              transform: `translate(${eyeShiftX}px, ${eyeShiftY}px)`,
              transition: 'transform 0.15s ease-out',
            }}
          >
            {/* Left Eye */}
            <g className="mascot-eye left-eye">
              {/* White Sclera */}
              <ellipse
                cx="112"
                cy="135"
                rx="18"
                ry="26"
                fill="url(#eyeScleraGrad)"
                stroke="#020617"
                strokeWidth="2.5"
              />
              {/* Emerald Pupil & Iris */}
              <ellipse
                cx={isThinking ? '114' : '115'}
                cy={isThinking ? '130' : '136'}
                rx="10"
                ry="17"
                fill="url(#pupilIrisGrad)"
              />
              {/* Twin 3D Catchlight Reflections */}
              <circle cx="118" cy="129" r="4" fill="#ffffff" />
              <circle cx="111" cy="142" r="2" fill="#6ee7b7" />
            </g>

            {/* Right Eye */}
            <g className="mascot-eye right-eye">
              {/* White Sclera */}
              <ellipse
                cx="168"
                cy="135"
                rx="18"
                ry="26"
                fill="url(#eyeScleraGrad)"
                stroke="#020617"
                strokeWidth="2.5"
              />
              {/* Emerald Pupil & Iris */}
              <ellipse
                cx={isThinking ? '166' : '165'}
                cy={isThinking ? '130' : '136'}
                rx="10"
                ry="17"
                fill="url(#pupilIrisGrad)"
              />
              {/* Twin 3D Catchlight Reflections */}
              <circle cx="169" cy="129" r="4" fill="#ffffff" />
              <circle cx="162" cy="142" r="2" fill="#6ee7b7" />
            </g>

            {/* Speaking Audio Cadence Wave under eyes */}
            {isSpeaking && (
              <g className="mascot-talking-mouth">
                <path
                  d="M 126 172 Q 140 182 154 172"
                  stroke="#34d399"
                  strokeWidth="3"
                  strokeLinecap="round"
                  fill="none"
                  opacity="0.85"
                />
              </g>
            )}
          </g>

          {/* ══════════════ 3. DYNAMIC 3D GROUND SHADOW ══════════════ */}
          <ellipse
            cx="140"
            cy="248"
            rx="58"
            ry="11"
            fill="rgba(0, 0, 0, 0.45)"
            className="ball-ground-shadow"
          />
        </svg>
      </div>
    </div>
  )
}

export default XerenMascot
