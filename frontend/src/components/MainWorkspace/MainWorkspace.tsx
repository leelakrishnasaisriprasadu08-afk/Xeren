import React from 'react'
import type { PresenceState } from '../../types/presence'
import type { Message } from '../../types/conversation'
import type { AgentMilestone, AgentProgressDetails } from '../../types/agent'
import { XerenPresence } from '../XerenPresence/XerenPresence'
import { CapabilityCards } from '../CapabilityCards/CapabilityCards'
import { Conversation } from '../Conversation/Conversation'
import { AgentActivity } from '../AgentActivity/AgentActivity'
import { MessageComposer } from '../MessageComposer/MessageComposer'
import { SuggestionChips } from '../SuggestionChips/SuggestionChips'
import './MainWorkspace.css'

interface MainWorkspaceProps {
  presenceState: PresenceState
  activeAmplitude: number
  prefersReducedMotion: boolean
  messages: Message[]
  currentStreamingText: string
  currentStreamingId: string | null
  agentProgress: AgentProgressDetails | null
  activeMilestone: AgentMilestone | null
  isListening: boolean
  isSpeaking: boolean
  voiceError?: string | null
  onSendMessage: (text: string) => void
  onStartListening: () => void
  onStopListening: () => void
  onInterrupt: () => void
}

export const MainWorkspace: React.FC<MainWorkspaceProps> = ({
  presenceState,
  activeAmplitude,
  prefersReducedMotion,
  messages,
  currentStreamingText,
  currentStreamingId,
  agentProgress,
  activeMilestone,
  isListening,
  isSpeaking,
  voiceError,
  onSendMessage,
  onStartListening,
  onStopListening,
  onInterrupt,
}) => {
  const hasMessages = messages.length > 0 || !!currentStreamingText

  return (
    <main className="main-workspace" role="main" data-testid="main-workspace">
      <div className="workspace-scroll-area">
        {/* Central Hero / Welcome Area */}
        <section className="workspace-hero" aria-label="AI Presence Stage">
          {/* Holographic Presence Orb */}
          <div className="workspace-presence-wrap">
            <XerenPresence
              state={presenceState}
              amplitude={activeAmplitude}
              isReducedMotion={prefersReducedMotion}
              onClick={() => {
                if (isListening) {
                  onStopListening()
                } else if (presenceState === 'speaking' || isSpeaking) {
                  onInterrupt()
                } else {
                  onStartListening()
                }
              }}
            />
          </div>

          {/* Welcome Headline */}
          <h2 className="workspace-greeting">
            Hello, I'm <span className="xeren-highlight">Xeren</span>
          </h2>

          <p className="workspace-subtitle">
            Your AI companion for research, creation and automation.
            <br />
            Ask me anything, or tell me what you want to build.
          </p>

          {/* Quick 4 Capability Entry Points */}
          <CapabilityCards onSelectPrompt={onSendMessage} />
        </section>

        {/* Live Conversation Stream (renders when messages exist) */}
        {hasMessages && (
          <section className="workspace-conversation-wrap" aria-label="Conversation Thread">
            <Conversation
              messages={messages}
              currentStreamingText={currentStreamingText}
              currentStreamingId={currentStreamingId}
            />
          </section>
        )}
      </div>

      {/* Bottom Dock: Agent Milestone + Message Composer + Suggestion Chips */}
      <footer className="workspace-dock" role="contentinfo">
        {/* Subtle Autonomous Agent milestone progress indicator */}
        <AgentActivity
          progressDetails={agentProgress}
          activeMilestone={activeMilestone}
        />

        {/* Large Premium Message Composer */}
        <MessageComposer
          presenceState={presenceState}
          isListening={isListening}
          isSpeaking={isSpeaking}
          voiceError={voiceError}
          onSendMessage={onSendMessage}
          onStartListening={onStartListening}
          onStopListening={onStopListening}
          onInterrupt={onInterrupt}
        />

        {/* Suggestion Chips */}
        <SuggestionChips onSelectSuggestion={onSendMessage} />
      </footer>
    </main>
  )
}
