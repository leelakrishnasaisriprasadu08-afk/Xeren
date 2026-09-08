import { useState, useEffect } from 'react'

export function useReducedMotion() {
  const [systemReducedMotion, setSystemReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  const [override, setOverride] = useState<boolean | null>(() => {
    if (typeof localStorage === 'undefined') return null
    const stored = localStorage.getItem('xeren_reduced_motion')
    return stored !== null ? stored === 'true' : null
  })

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handler = (e: MediaQueryListEvent) => setSystemReducedMotion(e.matches)

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler)
      return () => mediaQuery.removeEventListener('change', handler)
    } else {
      mediaQuery.addListener(handler)
      return () => mediaQuery.removeListener(handler)
    }
  }, [])

  const setReducedMotionOverride = (value: boolean | null) => {
    setOverride(value)
    if (typeof localStorage !== 'undefined') {
      if (value === null) {
        localStorage.removeItem('xeren_reduced_motion')
      } else {
        localStorage.setItem('xeren_reduced_motion', String(value))
      }
    }
  }

  const prefersReducedMotion = override !== null ? override : systemReducedMotion

  return {
    prefersReducedMotion,
    setReducedMotionOverride,
    isOverridden: override !== null,
  }
}
