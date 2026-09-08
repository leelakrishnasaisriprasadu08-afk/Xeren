import React, { useMemo } from 'react'
import type { PresenceState } from '../../types/presence'
import { SpecterOrb, type SpecterOrbProps } from './SpecterOrb'
import { XEREN_SPECTER_THEMES } from './specterOrb.presets'
export interface XerenSpecterOrbProps extends Omit<SpecterOrbProps, 'colorA' | 'colorB' | 'colorC'> {
  state?: PresenceState
  amplitude?: number
  isReducedMotion?: boolean
}

export const XerenSpecterOrb: React.FC<XerenSpecterOrbProps> = ({
  state = 'idle',
  amplitude = 0,
  isReducedMotion = false,
  width = '100%',
  height = '100%',
  className,
  maskRadius = 0,
  maskFeather = 0.3,
  zoom = 0.86,
  noiseScale = 0.85,
  cursorLight = 0.2,
  children,
  ...customProps
}) => {
  const theme = XEREN_SPECTER_THEMES[state] || XEREN_SPECTER_THEMES.idle

  // Keep turbulence very gentle and restrained even during speaking/listening
  const dynamicTurbulence = useMemo(() => {
    return Math.min(theme.turbulence + amplitude * 0.04, 0.3)
  }, [theme.turbulence, amplitude])

  // Minimize orb movement speed during listening and speaking for calm, organic presence
  const dynamicFlowSpeed = useMemo(() => {
    if (isReducedMotion) return 0
    return theme.flowSpeed + amplitude * 0.03
  }, [theme.flowSpeed, amplitude, isReducedMotion])

  // Express voice response primarily through luminous glow and rim sheen
  const dynamicGlow = useMemo(() => {
    return theme.glowStrength + amplitude * 0.35
  }, [theme.glowStrength, amplitude])

  const dynamicRim = useMemo(() => {
    return theme.rimStrength + amplitude * 0.2
  }, [theme.rimStrength, amplitude])

  return (
    <SpecterOrb
      width={width}
      height={height}
      className={className}
      colorA={theme.colorA}
      colorB={theme.colorB}
      colorC={theme.colorC}
      specularColorA={theme.specularColorA}
      specularColorB={theme.specularColorB}
      rimStrength={dynamicRim}
      glowStrength={dynamicGlow}
      glowFalloff={theme.glowFalloff}
      turbulence={dynamicTurbulence}
      flowSpeed={dynamicFlowSpeed}
      zoom={zoom}
      maskRadius={maskRadius}
      maskFeather={maskFeather}
      noiseScale={noiseScale}
      cursorLight={cursorLight}
      backgroundColor="transparent"
      cursorInteraction={!isReducedMotion}
      paused={isReducedMotion}
      {...customProps}
    >
      {children}
    </SpecterOrb>
  )
}

export default XerenSpecterOrb
