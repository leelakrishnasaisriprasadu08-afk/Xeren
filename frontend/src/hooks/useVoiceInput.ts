import { useState, useRef, useCallback, useEffect } from 'react'
import { VoiceInputService } from '../services/voiceService'

export function useVoiceInput() {
  const [isListening, setIsListening] = useState(false)
  const [amplitude, setAmplitude] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [permissionGranted, setPermissionGranted] = useState<boolean | null>(null)

  const serviceRef = useRef<VoiceInputService | null>(null)

  if (!serviceRef.current) {
    serviceRef.current = new VoiceInputService()
  }

  const stopListening = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.stopListening()
    }
    setIsListening(false)
    setAmplitude(0)
  }, [])

  const startListening = useCallback(
    async (
      onTranscriptChunk?: (transcript: string, isFinal: boolean) => void,
      onErrorCallback?: (err: Error) => void
    ) => {
      setError(null)
      try {
        const service = serviceRef.current!
        const supported = service.isSupported()
        if (!supported) {
          const notSupportedErr = new Error('Microphone or Audio API is not supported in this browser.')
          setError(notSupportedErr.message)
          onErrorCallback?.(notSupportedErr)
          return false
        }

        await service.startListening({
          onTranscriptChunk,
          onAmplitudeChange: (amp) => {
            setAmplitude(amp)
          },
          onError: (err) => {
            setError(err.message)
            setIsListening(false)
            setAmplitude(0)
            onErrorCallback?.(err)
          },
          onEnd: () => {
            setIsListening(false)
            setAmplitude(0)
          },
        })

        setIsListening(true)
        setPermissionGranted(true)
        return true
      } catch (err: any) {
        setIsListening(false)
        setAmplitude(0)
        const errMsg = err?.name === 'NotAllowedError' || err?.message?.includes('Permission denied')
          ? 'Microphone permission was denied. Please grant microphone access in browser settings or use text chat.'
          : err?.message || 'Failed to access microphone.'
        setError(errMsg)
        setPermissionGranted(false)
        onErrorCallback?.(new Error(errMsg))
        return false
      }
    },
    []
  )

  useEffect(() => {
    return () => {
      if (serviceRef.current) {
        serviceRef.current.stopListening()
      }
    }
  }, [])

  return {
    isListening,
    amplitude,
    error,
    permissionGranted,
    startListening,
    stopListening,
    clearError: () => setError(null),
  }
}
