import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MainWorkspace } from '../components/MainWorkspace/MainWorkspace'
import type { Message } from '../types/conversation'

describe('Two-Layer Layout (Clean Top Mascot Stage & Bottom Chat Workspace)', () => {
  const baseProps = {
    presenceState: 'idle' as const,
    activeAmplitude: 0.2,
    prefersReducedMotion: false,
    messages: [] as Message[],
    currentStreamingText: '',
    currentStreamingId: null,
    agentProgress: null,
    activeMilestone: null,
    isListening: false,
    isSpeaking: false,
    onSendMessage: vi.fn(),
    onStartListening: vi.fn(),
    onStopListening: vi.fn(),
    onInterrupt: vi.fn(),
  }

  it('renders both the top layer (AI Entity Stage) and bottom layer (User Chat Interface)', () => {
    const { container } = render(<MainWorkspace {...baseProps} />)

    const topLayer = container.querySelector('.workspace-top-layer')
    const bottomLayer = container.querySelector('.workspace-bottom-layer')

    expect(topLayer).toBeInTheDocument()
    expect(bottomLayer).toBeInTheDocument()
    expect(container.querySelector('.top-layer-orb-wrapper')).toBeInTheDocument()
    // Speech bubble removed per user request
    expect(container.querySelector('.top-layer-speech-bubble')).toBeNull()
  })

  it('dynamically switches between spacious-stage (welcome) and compact-stage (chatting)', () => {
    // Empty messages -> spacious stage
    const { container, rerender } = render(<MainWorkspace {...baseProps} messages={[]} />)
    expect(container.querySelector('.workspace-top-layer')).toHaveClass('spacious-stage')

    // Active messages -> compact stage
    const messages: Message[] = [
      { id: '1', role: 'user', content: 'What can you do?', timestamp: Date.now() },
      { id: '2', role: 'assistant', content: 'I am Xeren, ready to assist.', timestamp: Date.now() },
    ]
    rerender(<MainWorkspace {...baseProps} messages={messages} />)
    expect(container.querySelector('.workspace-top-layer')).toHaveClass('compact-stage')
  })
})
