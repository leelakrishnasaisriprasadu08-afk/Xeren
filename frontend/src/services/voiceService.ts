/**
 * Real-time Voice Input and Voice Output services using Web Audio API and Speech APIs.
 */

export interface VoiceInputCallbacks {
  onTranscriptChunk?: (transcript: string, isFinal: boolean) => void
  onAmplitudeChange?: (amplitude: number) => void
  onError?: (error: Error) => void
  onEnd?: () => void
}

export class VoiceInputService {
  private mediaStream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private animationFrameId: number | null = null
  // SpeechRecognition instance if supported by browser
  private recognition: any = null
  private isListening: boolean = false

  public isSupported(): boolean {
    const hasMedia = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia
    return hasMedia
  }

  public async requestPermission(): Promise<boolean> {
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        return false
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Stop initial stream immediately after permission check
      stream.getTracks().forEach((t) => t.stop())
      return true
    } catch {
      return false
    }
  }

  public async startListening(callbacks: VoiceInputCallbacks): Promise<void> {
    if (this.isListening) {
      return
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      // 1. Setup Audio Analyser for live amplitude
      const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext
      if (AudioCtxClass) {
        this.audioContext = new AudioCtxClass()
        if (this.audioContext.state === 'suspended') {
          await this.audioContext.resume()
        }
        const source = this.audioContext.createMediaStreamSource(this.mediaStream)
        this.analyser = this.audioContext.createAnalyser()
        this.analyser.fftSize = 128
        source.connect(this.analyser)

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount)
        const trackAmplitude = () => {
          if (!this.analyser || !this.isListening) return
          this.analyser.getByteFrequencyData(dataArray)
          let sum = 0
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i]
          }
          const avg = sum / dataArray.length
          const normalized = Math.min(1, Math.max(0, avg / 128))
          callbacks.onAmplitudeChange?.(normalized)
          this.animationFrameId = requestAnimationFrame(trackAmplitude)
        }
        this.isListening = true
        trackAmplitude()
      } else {
        this.isListening = true
      }

      // 2. Setup Speech Recognition if available
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (SpeechRecognition) {
        this.recognition = new SpeechRecognition()
        this.recognition.continuous = true
        this.recognition.interimResults = true
        this.recognition.lang = 'en-US'

        this.recognition.onresult = (event: any) => {
          let interimTranscript = ''
          let finalTranscript = ''
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript
            } else {
              interimTranscript += event.results[i][0].transcript
            }
          }
          const text = finalTranscript || interimTranscript
          if (text) {
            callbacks.onTranscriptChunk?.(text, !!finalTranscript)
          }
        }

        this.recognition.onerror = (event: any) => {
          if (event.error !== 'no-speech') {
            callbacks.onError?.(new Error(`Speech recognition error: ${event.error}`))
          }
        }

        this.recognition.onend = () => {
          if (this.isListening) {
            callbacks.onEnd?.()
          }
        }

        try {
          this.recognition.start()
        } catch {
          // Ignore if already running
        }
      }
    } catch (err: any) {
      this.stopListening()
      callbacks.onError?.(err instanceof Error ? err : new Error(String(err)))
      throw err
    }
  }

  public stopListening(): void {
    this.isListening = false

    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId)
      this.animationFrameId = null
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop())
      this.mediaStream = null
    }

    if (this.audioContext) {
      this.audioContext.close().catch(() => {})
      this.audioContext = null
    }

    if (this.recognition) {
      try {
        this.recognition.stop()
      } catch {}
      this.recognition = null
    }
  }

  public get listening(): boolean {
    return this.isListening
  }
}

export interface VoiceOutputCallbacks {
  onStart?: () => void
  onEnd?: () => void
  onInterrupted?: () => void
  onAmplitudeChange?: (amplitude: number) => void
  onError?: (error: Error) => void
}

export class VoiceOutputService {
  private isSpeakingState: boolean = false
  private currentUtterance: SpeechSynthesisUtterance | null = null
  private animationFrameId: number | null = null

  public isSupported(): boolean {
    return typeof window !== 'undefined' && 'speechSynthesis' in window
  }

  public speak(text: string, callbacks?: VoiceOutputCallbacks): void {
    this.stop() // Interrupt any previous speech

    if (!text.trim() || typeof window === 'undefined' || !window.speechSynthesis) {
      callbacks?.onEnd?.()
      return
    }

    this.isSpeakingState = true
    callbacks?.onStart?.()

    const utterance = new SpeechSynthesisUtterance(text)
    this.currentUtterance = utterance
    utterance.rate = 1.05
    utterance.pitch = 1.0

    // Try to pick a natural high-quality voice if available
    const voices = window.speechSynthesis.getVoices?.() || []
    const preferredVoice = voices.find(
      (v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Neural') || v.name.includes('Google') || v.name.includes('Samantha'))
    )
    if (preferredVoice) {
      utterance.voice = preferredVoice
    }

    // Simulated speech wave oscillation for presence synchronization
    let phase = 0
    const simulateAmplitude = () => {
      if (!this.isSpeakingState) return
      phase += 0.2
      // Rhythmic speech wave between 0.2 and 0.85
      const wave = (Math.sin(phase) + Math.cos(phase * 1.7) + 2) / 4
      const amplitude = Math.max(0.15, Math.min(0.9, wave))
      callbacks?.onAmplitudeChange?.(amplitude)
      this.animationFrameId = requestAnimationFrame(simulateAmplitude)
    }
    simulateAmplitude()

    utterance.onend = () => {
      this.isSpeakingState = false
      if (this.animationFrameId !== null) {
        cancelAnimationFrame(this.animationFrameId)
        this.animationFrameId = null
      }
      callbacks?.onAmplitudeChange?.(0)
      callbacks?.onEnd?.()
      this.currentUtterance = null
    }

    utterance.onerror = (event: any) => {
      this.isSpeakingState = false
      if (this.animationFrameId !== null) {
        cancelAnimationFrame(this.animationFrameId)
        this.animationFrameId = null
      }
      callbacks?.onAmplitudeChange?.(0)
      if (event.error === 'interrupted' || event.error === 'canceled') {
        callbacks?.onInterrupted?.()
      } else {
        callbacks?.onError?.(new Error(`Speech synthesis error: ${event.error}`))
      }
      this.currentUtterance = null
    }

    window.speechSynthesis.speak(utterance)
  }

  public stop(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId)
      this.animationFrameId = null
    }

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }

    this.isSpeakingState = false
    this.currentUtterance = null
  }

  public get isSpeaking(): boolean {
    return this.isSpeakingState
  }

  public get utterance(): SpeechSynthesisUtterance | null {
    return this.currentUtterance
  }
}
