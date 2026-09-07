import React, { useState, useEffect, useCallback } from 'react'
import { useConversation } from './hooks/useConversation'
import { useReducedMotion } from './hooks/useReducedMotion'
import { TopHeader } from './components/TopHeader/TopHeader'
import { Sidebar } from './components/Sidebar/Sidebar'
import { MainWorkspace } from './components/MainWorkspace/MainWorkspace'
import { RightSidebar } from './components/RightSidebar/RightSidebar'
import { MoreMenu } from './components/MoreMenu/MoreMenu'
import { AtmosphericBackground } from './components/AtmosphericBackground/AtmosphericBackground'
import { LandingPage } from './components/LandingPage/LandingPage'
import { GlowCursor } from './components/GlowCursor'
import { XEREN_SPECTER_THEMES } from './components/SpecterOrb/specterOrb.presets'
import './App.css'

export interface AppProps {
  initialView?: 'landing' | 'workspace'
}

export const App: React.FC<AppProps> = ({ initialView }) => {
  const isTestEnv = import.meta.env.MODE === 'test'
  const [currentView, setCurrentView] = useState<'landing' | 'workspace'>(() => {
    if (initialView) return initialView
    if (typeof window !== 'undefined') {
      if (window.location.hash === '#workspace') return 'workspace'
      if (window.location.hash === '#landing') return 'landing'
    }
    return isTestEnv ? 'workspace' : 'landing'
  })

  const { prefersReducedMotion, setReducedMotionOverride } = useReducedMotion()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false)

  const {
    presenceState,
    messages,
    currentStreamingText,
    currentStreamingId,
    agentProgress,
    activeMilestone,
    activeAmplitude,
    isListening,
    isSpeaking,
    isVoiceOutputEnabled,
    setIsVoiceOutputEnabled,
    connectionState,
    transportType,
    switchTransport,
    reconnect,
    voiceInputError,
    startListening,
    stopListening,
    sendMessage,
    interrupt,
    clearHistory,
  } = useConversation()

  // Global Keyboard Shortcuts
  const handleGlobalKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName?.toLowerCase()
      const isInputActive = activeTag === 'input' || activeTag === 'textarea'

      // Barge-in shortcut: Escape key
      if (e.key === 'Escape') {
        if (isListening || presenceState === 'listening') {
          e.preventDefault()
          stopListening()
        } else if (
          presenceState === 'speaking' ||
          presenceState === 'acting' ||
          presenceState === 'thinking' ||
          isSpeaking ||
          currentStreamingId
        ) {
          e.preventDefault()
          interrupt()
        }
        return
      }

      // Voice shortcut: Space or 'm' (only if not inside text input)
      if (!isInputActive && (e.code === 'Space' || e.key.toLowerCase() === 'm')) {
        e.preventDefault()
        if (isListening) {
          stopListening()
        } else {
          startListening()
        }
      }
    },
    [presenceState, isSpeaking, currentStreamingId, interrupt, isListening, stopListening, startListening]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [handleGlobalKeyDown])

  const currentTheme = XEREN_SPECTER_THEMES[presenceState] || XEREN_SPECTER_THEMES.idle
  const cursorColor = currentView === 'landing' ? '#00f0ff' : currentTheme.colorA
  const cursorSecondaryColor = currentView === 'landing' ? '#a855f7' : currentTheme.colorB

  const mainView =
    currentView === 'landing' ? (
      <LandingPage
        onEnterWorkspace={() => {
          setCurrentView('workspace')
          if (typeof window !== 'undefined') {
            window.location.hash = '#workspace'
          }
        }}
      />
    ) : (
      <div className={`app-shell app-container ${prefersReducedMotion ? 'reduced-motion' : ''}`}>
        {/* Cinematic Computational Atmospheric Background */}
        <AtmosphericBackground
          state={presenceState}
          isReducedMotion={prefersReducedMotion}
        />

        {/* 1. TOP HEADER */}
        <TopHeader
          connectionState={connectionState}
          transportType={transportType}
          onReconnect={reconnect}
          onOpenSettings={() => setIsMenuOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          onToggleRightPanel={() => setIsRightPanelOpen((prev) => !prev)}
          onViewLanding={() => {
            setCurrentView('landing')
            if (typeof window !== 'undefined') {
              window.location.hash = '#landing'
            }
          }}
        />

        {/* 3-COLUMN WORKSPACE LAYOUT */}
        <div className="app-body-layout">
          {/* Mobile overlay backdrop */}
          <div
            className={`mobile-overlay ${isSidebarOpen || isRightPanelOpen ? 'active' : ''}`}
            onClick={() => {
              setIsSidebarOpen(false)
              setIsRightPanelOpen(false)
            }}
            aria-hidden="true"
          />

          {/* 2. LEFT SIDEBAR */}
          <Sidebar
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
            onOpenSettings={() => setIsMenuOpen(true)}
            onSelectNav={(id) => {
              if (id === 'chat') {
                sendMessage('Start a fresh conversation')
              }
            }}
          />

          {/* 3. CENTRAL MAIN WORKSPACE */}
          <MainWorkspace
            presenceState={presenceState}
            activeAmplitude={activeAmplitude}
            prefersReducedMotion={prefersReducedMotion}
            messages={messages}
            currentStreamingText={currentStreamingText}
            currentStreamingId={currentStreamingId}
            agentProgress={agentProgress}
            activeMilestone={activeMilestone}
            isListening={isListening}
            isSpeaking={isSpeaking}
            voiceError={voiceInputError}
            onSendMessage={(text) => sendMessage(text, 'text')}
            onStartListening={startListening}
            onStopListening={stopListening}
            onInterrupt={interrupt}
          />

          {/* 4. RIGHT SIDEBAR (Quick Actions + System Status) */}
          <RightSidebar
            isOpen={isRightPanelOpen}
            transportType={transportType}
            connectionState={connectionState}
            onSelectPrompt={(prompt) => sendMessage(prompt, 'text')}
            onClose={() => setIsRightPanelOpen(false)}
          />
        </div>

        {/* Settings Modal / Menu */}
        <MoreMenu
          isOpen={isMenuOpen}
          onClose={() => setIsMenuOpen(false)}
          transportType={transportType}
          onSwitchTransport={switchTransport}
          isVoiceOutputEnabled={isVoiceOutputEnabled}
          onToggleVoiceOutput={setIsVoiceOutputEnabled}
          isReducedMotion={prefersReducedMotion}
          onToggleReducedMotion={(val) => setReducedMotionOverride(val)}
          onClearHistory={clearHistory}
        />
      </div>
    )

  return (
    <GlowCursor
      color={cursorColor}
      secondaryColor={cursorSecondaryColor}
      trailLength={36}
      trailWidth={6}
      trailTaper={0.8}
      followSpeed={0.26}
      glowIntensity={2.2}
      glowSpread={1.2}
      hotspot={0.68}
      brightness={1.25}
      opacity={0.95}
      pulseSpeed={1.2}
      noiseStrength={0.04}
      idleFade
      idleTimeout={750}
      fadeDuration={900}
      blendMode="screen"
      className="global-glow-cursor-app"
      data-testid="global-glow-cursor"
    >
      {mainView}
    </GlowCursor>
  )
}

export default App
