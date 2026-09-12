import { useState, useRef, useEffect, useCallback } from 'react'
import type { AgentMilestone, AgentProgressDetails } from '../types/agent'
import type { Message, MessageAttachment } from '../types/conversation'
import type { PresenceState } from '../types/presence'
import type { ServerEvent } from '../types/realtime'
import type { TransportType } from './useRealtimeConnection'
import { useRealtimeConnection } from './useRealtimeConnection'
import { useVoiceInput } from './useVoiceInput'
import { useVoiceOutput } from './useVoiceOutput'
import { playActivationSound, stopActivationSound } from '../services/activationSound'

export interface UseConversationOptions {
  initialTransportType?: TransportType
  enableSpeechSynthesis?: boolean
}

export function useConversation(options: UseConversationOptions = {}) {
  const { initialTransportType = 'mock', enableSpeechSynthesis = true } = options

  const [presenceState, setPresenceState] = useState<PresenceState>('idle')
  const [messages, setMessages] = useState<Message[]>([])
  const [currentStreamingText, setCurrentStreamingText] = useState<string>('')
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(null)
  const [agentProgress, setAgentProgress] = useState<AgentProgressDetails | null>(null)
  const [activeMilestone, setActiveMilestone] = useState<AgentMilestone | null>(null)
  const [isVoiceOutputEnabled, setIsVoiceOutputEnabled] = useState<boolean>(enableSpeechSynthesis)
  const [activationAmplitude, setActivationAmplitude] = useState<number>(0)

  const voiceInput = useVoiceInput()
  const voiceOutput = useVoiceOutput()
  const realtime = useRealtimeConnection({ initialType: initialTransportType })

  const completeTimeoutRef = useRef<any>(null)
  const interimTranscriptRef = useRef<string>('')
  const streamingTextRef = useRef<string>('')

  // Keep streamingTextRef synced for callbacks
  useEffect(() => {
    streamingTextRef.current = currentStreamingText
  }, [currentStreamingText])

  // Clear completion timeout on unmount
  useEffect(() => {
    return () => {
      if (completeTimeoutRef.current) {
        clearTimeout(completeTimeoutRef.current)
      }
      stopActivationSound()
    }
  }, [])

  const transitionToComplete = useCallback(() => {
    setPresenceState('complete')
    if (completeTimeoutRef.current) {
      clearTimeout(completeTimeoutRef.current)
    }
    completeTimeoutRef.current = setTimeout(() => {
      setPresenceState('idle')
    }, 1200)
  }, [])

  // Sync speaking state with voiceOutput
  useEffect(() => {
    if (voiceOutput.isSpeaking && presenceState !== 'speaking' && presenceState !== 'listening') {
      setPresenceState('speaking')
    } else if (!voiceOutput.isSpeaking && presenceState === 'speaking') {
      // If voice output stopped and we aren't streaming, transition to complete then idle
      if (!currentStreamingId) {
        transitionToComplete()
      }
    }
  }, [voiceOutput.isSpeaking, currentStreamingId, presenceState, transitionToComplete])

  // Barge-in / Interrupt handling
  const interrupt = useCallback(() => {
    // 1. Immediately cancel voice output and wake activation sound
    voiceOutput.stop()
    stopActivationSound()
    setActivationAmplitude(0)

    // 2. Tell transport server to cancel active response
    realtime.send({
      type: 'response.cancel',
      timestamp: Date.now(),
    })

    // 3. Commit any partial streaming text to messages if present
    if (streamingTextRef.current && currentStreamingId) {
      const partialMessage: Message = {
        id: currentStreamingId,
        role: 'xeren',
        content: streamingTextRef.current,
        timestamp: Date.now(),
        status: 'interrupted',
        isStreaming: false,
        interrupted: true,
        metadata: { interrupted: true },
      }
      setMessages((prev) => [...prev, partialMessage])
      setCurrentStreamingText('')
      setCurrentStreamingId(null)
    }

    // 4. Return presence to listening or idle
    if (voiceInput.isListening) {
      setPresenceState('listening')
    } else {
      setPresenceState('idle')
    }
  }, [voiceOutput, realtime, currentStreamingId, voiceInput.isListening])

  // Submit a message (either typed, spoken, or with attachments)
  const sendMessage = useCallback(
    (text: string, modality: 'text' | 'voice' = 'text', attachments?: MessageAttachment[]) => {
      const trimmed = text.trim()
      const hasAttachments = attachments && attachments.length > 0
      if (!trimmed && !hasAttachments) return

      // If Xeren is currently speaking or streaming, interrupt first
      if (presenceState === 'speaking' || presenceState === 'acting' || currentStreamingId) {
        interrupt()
      }

      const userMsg: Message = {
        id: `msg_user_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
        role: 'user',
        content: trimmed || (hasAttachments ? `[Shared ${attachments.length} attachment(s)]` : ''),
        timestamp: Date.now(),
        status: 'complete',
        modality,
        attachments,
      }

      setMessages((prev) => [...prev, userMsg])
      setPresenceState('thinking')

      const images = (attachments || [])
        .filter((a) => a.isImage && a.dataUrl)
        .map((a) => ({ name: a.name, dataUrl: a.dataUrl!, mimeType: a.type || 'image/png' }))

      // Send client event
      realtime.send({
        type: 'user.text',
        text: trimmed || (hasAttachments ? `Shared ${attachments.length} attachment(s)` : ''),
        attachments,
        images,
        timestamp: Date.now(),
      })
    },
    [presenceState, currentStreamingId, interrupt, realtime]
  )

  // Start Voice Listening with Barge-in capability & Neural Wake sound
  const startListening = useCallback(async () => {
    // Barge-in: If Xeren was talking or working, stop immediately
    if (presenceState === 'speaking' || voiceOutput.isSpeaking || currentStreamingId) {
      interrupt()
    }

    setPresenceState('listening')
    interimTranscriptRef.current = ''

    // Trigger Neural Wake activation sound asynchronously (non-blocking)
    playActivationSound({
      onAmplitude: (amp) => setActivationAmplitude(amp),
      onEnd: () => setActivationAmplitude(0),
      onError: () => setActivationAmplitude(0),
    }).catch(() => {})

    const success = await voiceInput.startListening(
      (chunk, isFinal) => {
        interimTranscriptRef.current = chunk
        if (isFinal && chunk.trim()) {
          voiceInput.stopListening()
          sendMessage(chunk.trim(), 'voice')
        }
      },
      (_err) => {
        setPresenceState('error')
      }
    )

    if (!success) {
      setPresenceState('error')
    }
  }, [presenceState, voiceOutput, currentStreamingId, interrupt, voiceInput, sendMessage])

  const stopListening = useCallback(() => {
    stopActivationSound()
    setActivationAmplitude(0)
    voiceInput.stopListening()
    const transcript = interimTranscriptRef.current.trim()
    if (transcript) {
      sendMessage(transcript, 'voice')
      interimTranscriptRef.current = ''
    } else {
      if (presenceState === 'listening') {
        setPresenceState('idle')
      }
    }
  }, [voiceInput, sendMessage, presenceState])

  // Process Realtime Server Events
  useEffect(() => {
    const unsubscribe = realtime.addEventHandler((event: ServerEvent) => {
      switch (event.type) {
        case 'response.created': {
          setCurrentStreamingId(event.response.id)
          setCurrentStreamingText('')
          streamingTextRef.current = ''
          setPresenceState('thinking')
          break
        }

        case 'response.text.delta': {
          const deltaMsgId = event.messageId || 'streaming_asst'
          setCurrentStreamingId(deltaMsgId)
          setCurrentStreamingText((prev) => {
            const next = prev + event.delta
            streamingTextRef.current = next
            return next
          })
          if (presenceState !== 'speaking' && !voiceOutput.isSpeaking) {
            setPresenceState('thinking')
          }
          break
        }

        case 'response.text.complete':
        case 'response.text.done': {
          const finalContent = event.text || streamingTextRef.current
          const finalId = event.messageId || event.response_id || currentStreamingId || `msg_asst_${Date.now()}`

          const hasPlan = !!(event as any).plan || !!(event as any).plan_staged
          const assistantMsg: Message = {
            id: finalId,
            role: 'xeren',
            content: finalContent,
            timestamp: Date.now(),
            status: 'complete',
            isStreaming: false,
            metadata: {
              plan: (event as any).plan || null,
              planStaged: (event as any).plan_staged ?? hasPlan,
              research: (event as any).research || null,
              heldDataApplied: (event as any).held_data_applied || null,
            },
          }

          setMessages((prev) => {
            const filtered = prev.filter((m) => m.id !== finalId)
            return [...filtered, assistantMsg]
          })

          setCurrentStreamingText('')
          streamingTextRef.current = ''
          setCurrentStreamingId(null)

          // If voice output is enabled and not already speaking, synthesize speech
          if (isVoiceOutputEnabled && finalContent.trim() && !voiceOutput.isSpeaking) {
            setPresenceState('speaking')
            voiceOutput.speak(finalContent, {
              onEnd: () => {
                transitionToComplete()
              },
              onError: () => {
                transitionToComplete()
              },
              onInterrupted: () => {
                setPresenceState('listening')
              },
            })
          } else {
            transitionToComplete()
          }
          break
        }

        case 'response.audio.start':
        case 'response.audio.chunk': {
          setPresenceState('speaking')
          break
        }

        case 'response.audio.end':
        case 'response.done': {
          if (!voiceOutput.isSpeaking) {
            transitionToComplete()
          }
          break
        }

        case 'agent.status': {
          const phase = event.phase || event.details?.phase || event.details?.milestone
          if (phase) {
            setActiveMilestone(phase)
          }

          const progressDetails: AgentProgressDetails = event.details || {
            phase,
            milestone: phase,
            goal: event.activityTitle,
            progress_percent: event.progressPercent,
          }
          setAgentProgress(progressDetails)

          if (event.status === 'running' || phase !== 'completed') {
            setPresenceState('acting')
          } else if (event.status === 'completed' || phase === 'completed') {
            transitionToComplete()
          } else if (event.status === 'failed') {
            setPresenceState('error')
          }
          break
        }

        case 'error': {
          setPresenceState('error')
          break
        }

        default:
          break
      }
    })

    return () => {
      unsubscribe()
    }
  }, [realtime, presenceState, voiceOutput, isVoiceOutputEnabled, currentStreamingId, transitionToComplete])

  // Synchronize Amplitude for Orb reaction:
  // When listening: use voiceInput amplitude.
  // When speaking: use voiceOutput amplitude.
  const activeAmplitude =
    presenceState === 'listening'
      ? Math.max(voiceInput.amplitude, activationAmplitude)
      : presenceState === 'speaking'
      ? voiceOutput.amplitude
      : presenceState === 'thinking' || presenceState === 'acting'
      ? 0.25
      : 0

  const clearHistory = useCallback(() => {
    setMessages([])
    setCurrentStreamingText('')
    setCurrentStreamingId(null)
    setAgentProgress(null)
    setActiveMilestone(null)
    setPresenceState('idle')
  }, [])

  const proceedWithStagedPlan = useCallback(async (customPlanText?: string) => {
    try {
      await fetch('/api/plan/proceed', { method: 'POST' })
    } catch (_) {
      // Local fallback
    }
    sendMessage(customPlanText || 'proceed to the plan', 'text')
  }, [sendMessage])

  return {
    presenceState,
    setPresenceState,
    messages,
    currentStreamingText,
    currentStreamingId,
    agentProgress,
    activeMilestone,
    activeAmplitude,
    isListening: voiceInput.isListening,
    isSpeaking: voiceOutput.isSpeaking,
    isVoiceOutputEnabled,
    setIsVoiceOutputEnabled,
    connectionState: realtime.connectionState,
    transportType: realtime.transportType,
    switchTransport: realtime.switchTransport,
    reconnect: realtime.connect,
    voiceInputError: voiceInput.error,
    voiceOutputError: voiceOutput.error,
    startListening,
    stopListening,
    sendMessage,
    proceedWithStagedPlan,
    interrupt,
    clearHistory,
  }
}
