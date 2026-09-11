/**
 * Real-time transport abstractions: WebSocket transport and Mock dev transport.
 */

import type { ClientEvent, ConnectionState, ServerEvent } from '../types/realtime'
import { solveAnything } from './cognitiveSolver'

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
      return
    }

    // Offline / Standalone Fallback: Ensure user typed messages always receive an active response
    if (event.type === 'user.text' || event.type === 'conversation.item.create') {
      const query = event.type === 'user.text' ? event.text : event.item?.content?.[0]?.text || ''
      this.simulateOfflineResponse(query)
    }
  }

  private async simulateOfflineResponse(query: string): Promise<void> {
    const messageId = `msg-solver-${Date.now()}`
    this.emit({
      type: 'response.created',
      response: { id: messageId },
      timestamp: Date.now(),
    })

    let reply = ''
    try {
      // Call the Xeren FastAPI backend — 30s timeout so the model has time to think
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000)
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (res.ok) {
        const data = await res.json()
        // Parse all response fields from Xeren's StructuredAnswer / achat() format
        reply =
          data?.content ||
          data?.answer ||
          data?.verified_answer ||
          data?.deliverable ||
          (typeof data === 'string' ? data : '')
      }
    } catch (_) {
      // Standalone / offline mode — fall through to cognitiveSolver
    }

    if (!reply) {
      reply = solveAnything(query)
    }

    const words = reply.split(' ')
    words.forEach((word, idx) => {
      setTimeout(() => {
        this.emit({
          type: 'response.text.delta',
          delta: (idx === 0 ? '' : ' ') + word,
          messageId,
          timestamp: Date.now(),
        })
      }, 35 * (idx + 1))
    })

    setTimeout(() => {
      this.emit({
        type: 'response.text.complete',
        text: reply,
        messageId,
        timestamp: Date.now(),
      })
      this.emit({
        type: 'response.done',
        messageId,
        timestamp: Date.now(),
      })
    }, 35 * (words.length + 2))
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

  private async simulateResponse(query: string): Promise<void> {
    const messageId = `msg-${Date.now()}`
    const isTask =
      query.toLowerCase().includes('research') ||
      query.toLowerCase().includes('create') ||
      query.toLowerCase().includes('analyze') ||
      query.toLowerCase().includes('build') ||
      query.toLowerCase().includes('make') ||
      query.toLowerCase().includes('write') ||
      query.toLowerCase().includes('generate') ||
      query.toLowerCase().includes('design')

    // If it's a task, show agent activity phases first
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
    }

    // Try real Xeren backend first
    let responseText = ''
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000)
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (res.ok) {
        const data = await res.json()
        responseText =
          data?.content ||
          data?.answer ||
          data?.verified_answer ||
          data?.deliverable ||
          (typeof data === 'string' ? data : '')
      }
    } catch (_) {
      // Fall back to local cognitiveSolver
    }

    if (!responseText) {
      responseText = solveAnything(query)
    }

    const words = responseText.split(' ')
    const delay = isTask ? 3200 : 350
    const stepInterval = Math.max(15, Math.min(60, Math.floor(1200 / Math.max(1, words.length))))

    this.emit({
      type: 'response.created',
      response: { id: messageId },
      timestamp: Date.now(),
    })

    words.forEach((word, index) => {
      const stepDelay = delay + index * stepInterval
      const tId = setTimeout(() => {
        if (this.isCancelled) return
        this.emit({
          type: 'response.text.delta',
          delta: (index === 0 ? '' : ' ') + word,
          messageId,
          timestamp: Date.now(),
        })

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
