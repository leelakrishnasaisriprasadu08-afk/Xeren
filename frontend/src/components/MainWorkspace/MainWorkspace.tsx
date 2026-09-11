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
import type { CognitiveMode } from '../TopHeader/TopHeader'
import './MainWorkspace.css'

export interface MainWorkspaceProps {
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
  isVoiceOutputEnabled?: boolean
  onToggleVoiceOutput?: (enabled: boolean) => void
  voiceError?: string | null
  activeMode?: CognitiveMode
  onSelectMode?: (mode: CognitiveMode) => void
  activeCommandCenterTab?: 'freelance' | 'security' | 'research' | 'channels'
  onCommandCenterTabChange?: (tab: 'freelance' | 'security' | 'research' | 'channels') => void
  onSendMessage: (text: string) => void
  onProceedPlan?: (planText?: string) => void
  onRevisePlan?: (planId?: string) => void
  onCancelPlan?: (planId?: string) => void
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
  isVoiceOutputEnabled: _isVoiceOutputEnabled = true,
  onToggleVoiceOutput: _onToggleVoiceOutput,
  voiceError,
  activeMode = 'think',
  onSelectMode,
  activeCommandCenterTab: _activeCommandCenterTab,
  onCommandCenterTabChange: _onCommandCenterTabChange,
  onSendMessage,
  onProceedPlan,
  onRevisePlan,
  onCancelPlan,
  onStartListening,
  onStopListening,
  onInterrupt,
}) => {
  const hasMessages = messages.length > 0 || !!currentStreamingText

  const activeStagedPlan = messages
    .slice()
    .reverse()
    .find((m) => m.metadata?.planStaged && m.metadata?.plan)?.metadata?.plan

  const handleProceed = onProceedPlan || ((text) => onSendMessage(text || 'proceed to the plan'))

  return (
    <main className="main-workspace two-layer-layout" role="main" data-testid="main-workspace">
      {/* ══════════════ LAYER 1: TOP LAYER (XEREN PRESENCE MASCOT STAGE) ══════════════ */}
      <section className={`workspace-top-layer ${hasMessages ? 'compact-stage' : 'spacious-stage'}`} aria-label="AI Entity Stage">
        <div className="top-layer-inner">
          {/* Prominent Luminescent Xeren Mascot */}
          <div className="top-layer-orb-wrapper">
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
        </div>
      </section>

      {/* ══════════════ LAYER 2: BOTTOM LAYER (USER CHAT & INTERACTION INTERFACE) ══════════════ */}
      <section className="workspace-bottom-layer" aria-label="User Chat Interface">
        <div className="bottom-layer-scroll-area">
          {!hasMessages ? (
            <div className="workspace-welcome-view">
              <h2 className="workspace-greeting">
                Hello, I'm <span className="xeren-highlight">Xeren</span>
              </h2>

              <p className="workspace-subtitle">
                Your AI companion for research, creation and automation.
                <br />
                Ask me anything, or tell me what you want to build.
              </p>

              <CapabilityCards onSelectPrompt={onSendMessage} />
            </div>
          ) : (
            <div className="workspace-conversation-wrap" aria-label="Conversation Thread">
              <Conversation
                messages={messages}
                currentStreamingText={currentStreamingText}
                currentStreamingId={currentStreamingId}
                onProceedPlan={handleProceed}
                onRevisePlan={onRevisePlan}
                onCancelPlan={onCancelPlan}
              />
            </div>
          )}
        </div>

        {/* Docked Interaction Controls */}
        <footer className="workspace-dock" role="contentinfo">
          {/* Active Staged Plan Floating Quick-Bar */}
          {activeStagedPlan && presenceState !== 'acting' && presenceState !== 'thinking' && (
            <div
              className="active-staged-plan-dock-pill"
              data-testid="active-staged-plan-dock-pill"
            >
              <div className="dock-pill-left">
                <span className="dock-pill-dot" />
                <span className="dock-pill-title">Plan Waiting for Approval:</span>
                <span className="dock-pill-goal">{activeStagedPlan.goal || 'Autonomous Plan'}</span>
              </div>
              <button
                type="button"
                className="dock-pill-proceed-btn"
                onClick={() => handleProceed('proceed to the plan')}
                data-testid="dock-pill-proceed-btn"
              >
                <span>⚡ Proceed to the Plan</span>
              </button>
            </div>
          )}

          <AgentActivity
            progressDetails={agentProgress}
            activeMilestone={activeMilestone}
          />

          <MessageComposer
            presenceState={presenceState}
            isListening={isListening}
            isSpeaking={isSpeaking}
            voiceError={voiceError}
            activeMode={activeMode}
            onSelectMode={onSelectMode}
            onSendMessage={onSendMessage}
            onStartListening={onStartListening}
            onStopListening={onStopListening}
            onInterrupt={onInterrupt}
          />

          <SuggestionChips onSelectSuggestion={onSendMessage} />
        </footer>
      </section>
    </main>
  )
}

export default MainWorkspace
