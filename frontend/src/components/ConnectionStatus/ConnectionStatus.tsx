import React from 'react'
import type { ConnectionState } from '../../types/realtime'
import './ConnectionStatus.css'

interface ConnectionStatusProps {
  state: ConnectionState
  transportType: string
  onReconnect?: () => void
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  state,
  transportType,
  onReconnect,
}) => {
  const getStatusLabel = () => {
    switch (state) {
      case 'connected':
        return transportType === 'mock' ? 'Mock Mode' : 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'reconnecting':
        return 'Reconnecting...'
      case 'error':
        return 'Connection Error (Retry)'
      case 'offline':
      default:
        return 'Offline (Click to Connect)'
    }
  }

  const handleClick = () => {
    if (state !== 'connected' && state !== 'connecting') {
      onReconnect?.()
    }
  }

  return (
    <button
      type="button"
      className={`connection-status-pill status-${state}`}
      onClick={handleClick}
      aria-label={`Connection state: ${state}`}
      data-testid="connection-status-pill"
    >
      <span className="status-indicator-dot" />
      <span>{getStatusLabel()}</span>
    </button>
  )
}
