import { useState, useEffect } from 'react'

export type PerformanceTier = 'high' | 'medium' | 'low'

export interface PerformanceProfile {
  tier: PerformanceTier
  maxBackgroundParticles: number
  maxPresenceParticles: number
  enableGlowFilters: boolean
  enableComplexNetwork: boolean
  isMobile: boolean
}

export function useAdaptivePerformance(isReducedMotion = false): PerformanceProfile {
  const [profile, setProfile] = useState<PerformanceProfile>(() => {
    return evaluatePerformance(isReducedMotion)
  })

  useEffect(() => {
    const handleResize = () => {
      setProfile(evaluatePerformance(isReducedMotion))
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [isReducedMotion])

  return profile
}

function evaluatePerformance(isReducedMotion: boolean): PerformanceProfile {
  if (typeof window === 'undefined') {
    return {
      tier: 'medium',
      maxBackgroundParticles: 20,
      maxPresenceParticles: 30,
      enableGlowFilters: true,
      enableComplexNetwork: true,
      isMobile: false,
    }
  }

  const width = window.innerWidth
  const isMobile = width < 768
  const isTablet = width >= 768 && width < 1080

  // Check hardware concurrency if available
  const cores = navigator.hardwareConcurrency || 4
  const memory = (navigator as unknown as { deviceMemory?: number }).deviceMemory || 4

  if (isReducedMotion) {
    return {
      tier: 'low',
      maxBackgroundParticles: 0,
      maxPresenceParticles: 12,
      enableGlowFilters: false,
      enableComplexNetwork: false,
      isMobile,
    }
  }

  if (isMobile || cores <= 2 || memory <= 2) {
    return {
      tier: 'low',
      maxBackgroundParticles: 14,
      maxPresenceParticles: 22,
      enableGlowFilters: false,
      enableComplexNetwork: false,
      isMobile: true,
    }
  }

  if (isTablet || cores <= 4 || memory <= 4) {
    return {
      tier: 'medium',
      maxBackgroundParticles: 24,
      maxPresenceParticles: 36,
      enableGlowFilters: true,
      enableComplexNetwork: true,
      isMobile: false,
    }
  }

  // Desktop / High tier
  return {
    tier: 'high',
    maxBackgroundParticles: 32,
    maxPresenceParticles: 50,
    enableGlowFilters: true,
    enableComplexNetwork: true,
    isMobile: false,
  }
}
