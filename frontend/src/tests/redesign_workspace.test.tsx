import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'
import { TopHeader } from '../components/TopHeader/TopHeader'
import { Sidebar } from '../components/Sidebar/Sidebar'
import { CapabilityCards } from '../components/CapabilityCards/CapabilityCards'
import { SuggestionChips } from '../components/SuggestionChips/SuggestionChips'
import { RightSidebar } from '../components/RightSidebar/RightSidebar'

describe('Xeren Redesigned Workspace - Layout & Component Verification', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  // 1. Top Header
  it('renders TopHeader with brand title, Think/Reason/Create tabs, and System Ready badge', () => {
    render(
      <TopHeader
        connectionState="connected"
        transportType="mock"
        onOpenSettings={vi.fn()}
      />
    )

    expect(screen.getByText('XEREN')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Think' })).toHaveClass('active')
    expect(screen.getByRole('button', { name: 'Reason' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create' })).toBeInTheDocument()
    expect(screen.getByText('System Ready')).toBeInTheDocument()
    expect(screen.getByText('1.0 Presence')).toBeInTheDocument()
    expect(screen.getByTestId('settings-button')).toBeInTheDocument()
  })

  // 2. Left Sidebar
  it('renders Sidebar with vertical navigation, Beta badge on Web Agent, and promo card', () => {
    const onOpenSettings = vi.fn()
    const onSelectNav = vi.fn()

    render(
      <Sidebar
        isOpen={true}
        onOpenSettings={onOpenSettings}
        onSelectNav={onSelectNav}
      />
    )

    expect(screen.getByTestId('nav-item-home')).toHaveClass('active')
    expect(screen.getByTestId('nav-item-chat')).toBeInTheDocument()
    expect(screen.getByTestId('nav-item-web-agent')).toHaveTextContent('Beta')
    expect(screen.getByTestId('nav-item-plugins')).toBeInTheDocument()
    expect(screen.getByTestId('nav-item-knowledge')).toBeInTheDocument()
    expect(screen.getByTestId('nav-item-projects')).toBeInTheDocument()
    expect(screen.getByTestId('nav-item-settings')).toBeInTheDocument()
    expect(screen.getByText('Build. Automate. Grow.')).toBeInTheDocument()

    // Clicking settings item invokes callback
    fireEvent.click(screen.getByTestId('nav-item-settings'))
    expect(onOpenSettings).toHaveBeenCalledTimes(1)
  })

  // 3. Central Welcome Greeting & Capability Cards
  it('renders welcome greeting "Hello, I\'m Xeren" and the 4 capability cards', () => {
    render(<App />)

    expect(screen.getByText("Hello, I'm")).toBeInTheDocument()
    expect(screen.getByText('Xeren')).toBeInTheDocument()
    expect(screen.getByText(/Your AI companion for research, creation and automation/i)).toBeInTheDocument()

    // 4 Capability Cards
    expect(screen.getByTestId('capability-card-research')).toHaveTextContent('Find latest information')
    expect(screen.getByTestId('capability-card-create')).toHaveTextContent('Build websites & apps')
    expect(screen.getByTestId('capability-card-automate')).toHaveTextContent('Use AI agents & plugins')
    expect(screen.getByTestId('capability-card-solve')).toHaveTextContent('Get step-by-step help')
  })

  // 4. Clicking a Capability Card triggers conversation
  it('clicking a capability card submits a prompt into the conversation', async () => {
    const onSelectPrompt = vi.fn()
    render(<CapabilityCards onSelectPrompt={onSelectPrompt} />)

    fireEvent.click(screen.getByTestId('capability-card-create'))
    expect(onSelectPrompt).toHaveBeenCalledWith('Create a modern web application for my project')
  })

  // 5. Suggestion Chips
  it('renders all 4 suggestion chips below composer and clicking one sends prompt', () => {
    const onSelectSuggestion = vi.fn()
    render(<SuggestionChips onSelectSuggestion={onSelectSuggestion} />)

    expect(screen.getByText('Build a website for my startup')).toBeInTheDocument()
    expect(screen.getByText('Analyze the latest AI trends')).toBeInTheDocument()
    expect(screen.getByText('Find study resources')).toBeInTheDocument()
    expect(screen.getByText('Automate my workflow')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Automate my workflow'))
    expect(onSelectSuggestion).toHaveBeenCalledWith('Automate my workflow')
  })

  // 6. Right Sidebar with Quick Actions and Truthful System Status
  it('renders RightSidebar with Quick Actions and displays Mock Mode without hardcoded fake online status', () => {
    const onSelectPrompt = vi.fn()
    render(
      <RightSidebar
        isOpen={true}
        transportType="mock"
        connectionState="connected"
        onSelectPrompt={onSelectPrompt}
      />
    )

    // Quick Actions
    expect(screen.getByTestId('quick-action-create-site')).toHaveTextContent('Create Website')
    expect(screen.getByTestId('quick-action-research-topic')).toHaveTextContent('Research Topic')
    expect(screen.getByTestId('quick-action-use-plugins')).toHaveTextContent('Use Plugins')
    expect(screen.getByTestId('quick-action-view-projects')).toHaveTextContent('View Projects')

    fireEvent.click(screen.getByTestId('quick-action-create-site'))
    expect(onSelectPrompt).toHaveBeenCalled()

    // Truthful System Status (Displays Mock Mode when mock is used)
    expect(screen.getByTestId('mock-mode-callout')).toHaveTextContent('Mock Mode Active')
    expect(screen.getByText('Core Model')).toBeInTheDocument()
    expect(screen.getByText('RAG System')).toBeInTheDocument()
    expect(screen.getByText('Browser Agent')).toBeInTheDocument()
    expect(screen.getAllByText('Simulated').length).toBeGreaterThan(0)
  })

  // 7. Full App Integration & Interaction
  it('clicking suggestion chip inside App sends user message and starts AI thinking', async () => {
    render(<App />)

    // Verify exactly ONE global GlowCursor covers the total interface (no duplicates)
    expect(screen.getByTestId('global-glow-cursor')).toBeInTheDocument()
    expect(document.querySelectorAll('.glow-cursor__canvas')).toHaveLength(1)

    const chip = screen.getByTestId('suggestion-chip-analyze-the-latest-ai-trends')
    await act(async () => {
      fireEvent.click(chip)
    })

    // User message bubble appears in conversation along with the suggestion chip
    const occurrences = screen.getAllByText('Analyze the latest AI trends')
    expect(occurrences.length).toBeGreaterThanOrEqual(2)

    // Presence transitions to thinking
    const presence = screen.getByRole('status', { name: /ai presence/i })
    expect(presence).toHaveClass('state-thinking')
  })

  it('renders global GlowCursor wrapping the Landing view as well without duplicates', () => {
    render(<App initialView="landing" />)
    expect(screen.getByTestId('global-glow-cursor')).toBeInTheDocument()
    expect(document.querySelectorAll('.glow-cursor__canvas')).toHaveLength(1)
    expect(screen.getByTestId('landing-page')).toBeInTheDocument()
  })
})
