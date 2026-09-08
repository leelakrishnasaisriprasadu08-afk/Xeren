import { useState, useRef, useCallback, useEffect } from 'react'
import { VoiceOutputService } from '../services/voiceService'

export function useVoiceOutput() {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [amplitude, setAmplitude] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const serviceRef = useRef<VoiceOutputService | null>(null)

  if (!serviceRef.current) {
    serviceRef.current = new VoiceOutputService()
  }

  const stop = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.stop()
    }
    setIsSpeaking(false)
    setAmplitude(0)
  }, [])

  const speak = useCallback(
    (
      text: string,
      options?: {
        onStart?: () => void
        onEnd?: () => void
        onInterrupted?: () => void
        onError?: (err: Error) => void
      }
    ) => {
      setError(null)
      const service = serviceRef.current!

      service.speak(text, {
        onStart: () => {
          setIsSpeaking(true)
          options?.onStart?.()
        },
        onEnd: () => {
          setIsSpeaking(false)
          setAmplitude(0)
          options?.onEnd?.()
        },
        onInterrupted: () => {
          setIsSpeaking(false)
          setAmplitude(0)
          options?.onInterrupted?.()
        },
        onAmplitudeChange: (amp) => {
          setAmplitude(amp)
        },
        onError: (err) => {
          setIsSpeaking(false)
          setAmplitude(0)
          setError(err.message)
          options?.onError?.(err)
        },
      })
    },
    []
  )

  useEffect(() => {
    return () => {
      if (serviceRef.current) {
        serviceRef.current.stop()
      }
    }
  }, [])

  return {
    isSpeaking,
    amplitude,
    error,
    speak,
    stop,
    clearError: () => setError(null),
  }
}
