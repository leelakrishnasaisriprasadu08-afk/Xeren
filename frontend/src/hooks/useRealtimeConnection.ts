import { useState, useRef, useEffect, useCallback } from 'react'
import type { IRealtimeTransport } from '../services/realtimeTransport'
import {
  MockRealtimeTransport,
  WebSocketRealtimeTransport,
} from '../services/realtimeTransport'
import type { ClientEvent, ConnectionState, ServerEvent } from '../types/realtime'

export type TransportType = 'mock' | 'websocket'

interface UseRealtimeConnectionOptions {
  initialType?: TransportType
  wsUrl?: string
  autoConnect?: boolean
}

export function useRealtimeConnection(options: UseRealtimeConnectionOptions = {}) {
  const {
    initialType = 'mock',
    wsUrl = 'ws://localhost:8000/api/v1/realtime',
    autoConnect = true,
  } = options

  const [transportType, setTransportType] = useState<TransportType>(initialType)
  const [connectionState, setConnectionState] = useState<ConnectionState>('offline')
  const [lastError, setLastError] = useState<string | null>(null)

  const transportRef = useRef<IRealtimeTransport | null>(null)
  const listenersRef = useRef<Set<(event: ServerEvent) => void>>(new Set())

  // Initialize transport according to chosen type
  const createTransport = useCallback(
    (type: TransportType): IRealtimeTransport => {
      if (type === 'websocket') {
        return new WebSocketRealtimeTransport(wsUrl)
      }
      return new MockRealtimeTransport()
    },
    [wsUrl]
  )

  const connect = useCallback(async () => {
    if (!transportRef.current) {
      transportRef.current = createTransport(transportType)
    }

    try {
      setLastError(null)
      await transportRef.current.connect()
    } catch (err: any) {
      setLastError(err?.message || 'Connection failed')
    }
  }, [createTransport, transportType])

  const disconnect = useCallback(() => {
    if (transportRef.current) {
      transportRef.current.disconnect()
    }
  }, [])

  const switchTransport = useCallback(
    (newType: TransportType) => {
      if (transportRef.current) {
        transportRef.current.disconnect()
      }
      setTransportType(newType)
      const newTransport = createTransport(newType)
      transportRef.current = newTransport

      newTransport.onConnectionChange((state) => {
        setConnectionState(state)
        if (state === 'error') {
          setLastError('Connection error occurred.')
        }
      })

      newTransport.on((event) => {
        listenersRef.current.forEach((fn) => fn(event))
      })

      newTransport.connect().catch((err) => {
        setLastError(err?.message || 'Failed to connect with new transport')
      })
    },
    [createTransport]
  )

  const send = useCallback((event: ClientEvent) => {
    if (transportRef.current) {
      transportRef.current.send(event)
    }
  }, [])

  const addEventHandler = useCallback((handler: (event: ServerEvent) => void) => {
    listenersRef.current.add(handler)
    return () => {
      listenersRef.current.delete(handler)
    }
  }, [])

  useEffect(() => {
    const transport = createTransport(transportType)
    transportRef.current = transport

    const unsubState = transport.onConnectionChange((state) => {
      setConnectionState(state)
      if (state === 'error') {
        setLastError('Connection error occurred.')
      }
    })

    const unsubEvents = transport.on((event) => {
      listenersRef.current.forEach((fn) => fn(event))
    })

    if (autoConnect) {
      transport.connect().catch((err) => {
        setLastError(err?.message || 'Auto-connect failed')
      })
    }

    return () => {
      unsubState()
      unsubEvents()
      transport.disconnect()
      transportRef.current = null
    }
  }, [createTransport, transportType, autoConnect])

  return {
    connectionState,
    transportType,
    lastError,
    connect,
    disconnect,
    switchTransport,
    send,
    addEventHandler,
    getTransport: () => transportRef.current,
  }
}
