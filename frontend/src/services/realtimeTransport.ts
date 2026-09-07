/**
 * Real-time transport abstractions: WebSocket transport and Mock dev transport.
 */

import type { ClientEvent, ConnectionState, ServerEvent } from '../types/realtime'

export interface IRealtimeTransport {
  readonly state: ConnectionState
  connect(): Promise<void>
  disconnect(): void
  send(event: ClientEvent): void
  on(handler: (event: ServerEvent) => void): () => void
  onConnectionChange(handler: (state: ConnectionState) => void): () => void
}

/**
 * Standard WebSocket Transport for connecting to the future Xeren Realtime Gateway.
 */
export class WebSocketRealtimeTransport implements IRealtimeTransport {
  private ws: WebSocket | null = null
  private url: string
  private currentState: ConnectionState = 'offline'
  private handlers: Set<(event: ServerEvent) => void> = new Set()
  private stateHandlers: Set<(state: ConnectionState) => void> = new Set()
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectTimeoutId: any = null

  constructor(url: string = 'ws://localhost:8000/api/v1/realtime') {
    this.url = url
  }

  public get state(): ConnectionState {
    return this.currentState
  }

  public async connect(): Promise<void> {
    if (this.currentState === 'connected' || this.currentState === 'connecting') {
      return
    }

    this.setState('connecting')

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        this.setState('connected')
        this.send({
          type: 'conversation.start',
          timestamp: Date.now(),
        })
      }

      this.ws.onmessage = (messageEvent) => {
        try {
          const parsed = JSON.parse(messageEvent.data) as ServerEvent
          if (!parsed || !parsed.type) {
            console.warn('[RealtimeTransport] Discarded malformed server event:', messageEvent.data)
            return
          }
          this.emit(parsed)
        } catch (err) {
          console.warn('[RealtimeTransport] Failed to parse message JSON:', err)
        }
      }

      this.ws.onerror = () => {
        this.setState('error')
      }

      this.ws.onclose = () => {
        if (this.currentState !== 'offline') {
          this.attemptReconnect()
        }
      }
    } catch {
      this.setState('error')
      this.attemptReconnect()
    }
  }

  public disconnect(): void {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }
    this.setState('offline')
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  public send(event: ClientEvent): void {
    if (this.ws && this.currentState === 'connected') {
      this.ws.send(JSON.stringify(event))
    }
  }

  public on(handler: (event: ServerEvent) => void): () => void {
    this.handlers.add(handler)
    return () => {
      this.handlers.delete(handler)
    }
  }

  public onConnectionChange(handler: (state: ConnectionState) => void): () => void {
    this.stateHandlers.add(handler)
    handler(this.currentState)
    return () => {
      this.stateHandlers.delete(handler)
    }
  }

  private setState(newState: ConnectionState): void {
    this.currentState = newState
    this.stateHandlers.forEach((fn) => fn(newState))
  }

  private emit(event: ServerEvent): void {
    this.handlers.forEach((fn) => fn(event))
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setState('error')
      return
    }

    this.setState('reconnecting')
    this.reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 10000)

    this.reconnectTimeoutId = setTimeout(() => {
      this.connect().catch(() => {})
    }, delay)
  }
}

/**
 * Deterministic Mock Realtime Transport for development, offline testing, and demoing.
 */
export class MockRealtimeTransport implements IRealtimeTransport {
  private currentState: ConnectionState = 'offline'
  private handlers: Set<(event: ServerEvent) => void> = new Set()
  private stateHandlers: Set<(state: ConnectionState) => void> = new Set()
  private activeTimeouts: any[] = []
  private isCancelled: boolean = false

  public get state(): ConnectionState {
    return this.currentState
  }

  public async connect(): Promise<void> {
    this.setState('connecting')
    await new Promise((r) => setTimeout(r, 200))
    this.setState('connected')
  }

  public disconnect(): void {
    this.clearTimeouts()
    this.setState('offline')
  }

  public send(event: ClientEvent): void {
    if (event.type === 'response.cancel') {
      this.isCancelled = true
      this.clearTimeouts()
      return
    }

    if (event.type === 'user.text' || event.type === 'user.audio.end' || event.type === 'conversation.item.create') {
      this.isCancelled = false
      let query = 'Voice input received'
      if (event.type === 'user.text') {
        query = event.text
      } else if (event.type === 'conversation.item.create') {
        query = event.item?.content?.[0]?.text || 'User query'
      }
      this.simulateResponse(query)
    }
  }

  public on(handler: (event: ServerEvent) => void): () => void {
    this.handlers.add(handler)
    return () => {
      this.handlers.delete(handler)
    }
  }

  public onConnectionChange(handler: (state: ConnectionState) => void): () => void {
    this.stateHandlers.add(handler)
    handler(this.currentState)
    return () => {
      this.stateHandlers.delete(handler)
    }
  }

  public simulateError(message: string = 'Network failure'): void {
    this.setState('error')
    this.emit({
      type: 'error',
      code: 'ERR_SIMULATED',
      message,
      recoverable: true,
      timestamp: Date.now(),
    })
  }

  public simulateMalformedEvent(rawEvent: any): void {
    this.emit(rawEvent)
  }

  private setState(newState: ConnectionState): void {
    this.currentState = newState
    this.stateHandlers.forEach((fn) => fn(newState))
  }

  private emit(event: ServerEvent): void {
    this.handlers.forEach((fn) => fn(event))
  }

  private clearTimeouts(): void {
    this.activeTimeouts.forEach((id) => clearTimeout(id))
    this.activeTimeouts = []
  }

  private simulateResponse(query: string): void {
    const messageId = `msg-${Date.now()}`
    const isTask =
      query.toLowerCase().includes('research') ||
      query.toLowerCase().includes('create') ||
      query.toLowerCase().includes('analyze') ||
      query.toLowerCase().includes('build')

    // Determine canned response
    let responseText = `I am present. You asked about "${query}". I am ready to assist you.`
    if (query.toLowerCase().includes('hello') || query.toLowerCase().includes('hi')) {
      responseText = "Greetings. I am Xeren. What shall we achieve today?"
    } else if (isTask) {
      responseText = `I have orchestrated the task for "${query}". The plan was generated and verified.`
    }

    const words = responseText.split(' ')
    let delay = 350

    // If task, simulate Agent Activity milestones
    if (isTask) {
      const phases: Array<{ phase: any; title: string; delayOffset: number }> = [
        { phase: 'understanding', title: 'Understanding task objectives', delayOffset: 200 },
        { phase: 'planning', title: 'Formulating action plan', delayOffset: 700 },
        { phase: 'researching', title: 'Gathering contextual knowledge', delayOffset: 1200 },
        { phase: 'creating', title: 'Synthesizing output', delayOffset: 1800 },
        { phase: 'verifying', title: 'Verifying integrity', delayOffset: 2400 },
        { phase: 'completed', title: 'Task finalized', delayOffset: 2800 },
      ]

      phases.forEach((p) => {
        const tId = setTimeout(() => {
          if (this.isCancelled) return
          this.emit({
            type: 'agent.status',
            phase: p.phase,
            activityTitle: p.title,
            timestamp: Date.now(),
          })
        }, p.delayOffset)
        this.activeTimeouts.push(tId)
      })

      delay = 3000
    }

    // Audio start event
    const audioStartTid = setTimeout(() => {
      if (this.isCancelled) return
      this.emit({
        type: 'response.audio.start',
        messageId,
        timestamp: Date.now(),
      })
    }, delay)
    this.activeTimeouts.push(audioStartTid)

    // Stream text deltas word by word
    words.forEach((word, index) => {
      const stepDelay = delay + index * 100
      const tId = setTimeout(() => {
        if (this.isCancelled) return
        this.emit({
          type: 'response.text.delta',
          delta: (index === 0 ? '' : ' ') + word,
          messageId,
          timestamp: Date.now(),
        })

        // On final word
        if (index === words.length - 1) {
          this.emit({
            type: 'response.text.complete',
            text: responseText,
            messageId,
            timestamp: Date.now(),
          })

          this.emit({
            type: 'response.audio.end',
            messageId,
            timestamp: Date.now(),
          })
        }
      }, stepDelay)
      this.activeTimeouts.push(tId)
    })
  }
}
