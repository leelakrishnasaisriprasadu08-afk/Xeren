import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SelfImprovementHubModal } from '../components/SelfImprovementHubModal/SelfImprovementHubModal'
import { TopHeader } from '../components/TopHeader/TopHeader'
import { RightSidebar } from '../components/RightSidebar/RightSidebar'
import type {
  UserQueryPattern,
  SearchModelInsight,
  AdaptiveSystemDirective,
  SelfImprovementReport,
} from '../types/improvement'

const mockReport: SelfImprovementReport = {
  adaptive_score: 95.2,
  total_observations_recorded: 18,
  patterns_count: 2,
  insights_count: 1,
  active_directives_count: 2,
  evolution_cycles_completed: 2,
  recent_improvements: [
    'Synthesized Preemptive Session Isolation directive from repeated group collaboration questions',
    'Extracted TypeScript & FastAPI typed contract preferences',
  ],
  timestamp: '2026-09-07T12:00:00Z',
}

const mockPatterns: UserQueryPattern[] = [
  {
    pattern_id: 'uqp_collab_01',
    category: 'architecture',
    intent_cluster: 'collaboration_session_isolation',
    sample_queries: [
      'when two members asking doubts dont put interuptions',
      'attach to same project but different workstations',
    ],
    frequency_count: 5,
    confidence: 0.96,
    first_observed: '2026-09-07T10:00:00Z',
    last_observed: '2026-09-07T12:00:00Z',
    distilled_preference: 'User demands zero-interruption parallel workspaces with strict session isolation.',
    recommended_adaptation: 'Configure isolated WebSocket channels for each member and ground AI coach independently.',
    is_active: true,
  },
]

const mockInsights: SearchModelInsight[] = [
  {
    insight_id: 'smi_search_01',
    topic: 'WebSocket Parallelism & State Multiplexing',
    consensus_facts: [
      'Partitioning state by member prevents message interleaving across collaborative sessions.',
      'Heartbeat pings every 30 seconds prevent load balancer dropouts.',
    ],
    recurring_domains: ['fastapi.tiangolo.com', 'developer.mozilla.org'],
    failure_traps_identified: [
      'Shared global history arrays cause data bleed between concurrent users.',
    ],
    bot_models_evaluated: ['Claude 3.5 Sonnet', 'Gemini 2.0 Flash'],
    consensus_agreement_pct: 97.5,
    discovered_at: '2026-09-07T11:00:00Z',
  },
]

const mockDirectives: AdaptiveSystemDirective[] = [
  {
    directive_id: 'asd_directive_01',
    title: 'Preemptive Session Isolation Directive',
    category: 'query_routing',
    directive_prompt:
      'CRITICAL DIRECTIVE: Enforce strict (project_id, member_id) state isolation across concurrent workstations.',
    source_patterns: ['uqp_collab_01', 'smi_search_01'],
    effectiveness_score: 0.98,
    is_active: true,
    evolution_cycle: 1,
    created_at: '2026-09-07T10:30:00Z',
    updated_at: '2026-09-07T10:30:00Z',
  },
]

describe('Neural Learning & LLM Self-Improvement Hub', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, options?: any) => {
        if (url.includes('/api/llm/improvements/status')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockReport,
          })
        }
        if (url.includes('/api/llm/improvements/patterns')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockPatterns,
          })
        }
        if (url.includes('/api/llm/improvements/insights')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockInsights,
          })
        }
        if (url.includes('/api/llm/improvements/directives') && (!options || options.method !== 'PUT')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockDirectives,
          })
        }
        if (url.includes('/api/llm/improvements/analyze')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              ...mockReport,
              evolution_cycles_completed: 3,
              adaptive_score: 96.0,
            }),
          })
        }
        if (options && options.method === 'PUT') {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              ...mockDirectives[0],
              is_active: false,
            }),
          })
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({}),
        })
      })
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does not render when isOpen is false', () => {
    render(<SelfImprovementHubModal isOpen={false} onClose={vi.fn()} />)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('renders modal header, telemetry ribbon, and active score when open', async () => {
    render(
      <SelfImprovementHubModal
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
      />
    )

    expect(screen.getByRole('dialog')).toBeDefined()
    expect(screen.getByText(/Neural Learning & LLM Self-Improvement Hub/i)).toBeDefined()
    expect(screen.getByText(/95.2%/i)).toBeDefined()
    expect(screen.getByText(/Trigger Self-Improvement Cycle/i)).toBeDefined()
  })

  it('renders and allows switching between the 4 improvement tabs', async () => {
    render(
      <SelfImprovementHubModal
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
      />
    )

    // Wait for patterns to load in Tab 1
    await waitFor(() => {
      expect(screen.getByText(/COLLABORATION SESSION ISOLATION/i)).toBeDefined()
    })

    // Switch to Tab 2: Web Search & Bot Consensus
    const tab2Btn = screen.getByRole('button', { name: /Web Search & Bot Consensus/i })
    fireEvent.click(tab2Btn)

    await waitFor(() => {
      expect(screen.getByText(/WebSocket Parallelism & State Multiplexing/i)).toBeDefined()
      expect(screen.getByText(/Shared global history arrays cause data bleed/i)).toBeDefined()
    })

    // Switch to Tab 3: Evolved System Directives
    const tab3Btn = screen.getByRole('button', { name: /Evolved System Directives/i })
    fireEvent.click(tab3Btn)

    await waitFor(() => {
      expect(screen.getByText(/Preemptive Session Isolation Directive/i)).toBeDefined()
      expect(screen.getByText(/Active in Prompt/i)).toBeDefined()
    })

    // Switch to Tab 4: Adaptation Architecture
    const tab4Btn = screen.getByRole('button', { name: /Adaptation Architecture/i })
    fireEvent.click(tab4Btn)

    await waitFor(() => {
      expect(screen.getByText(/Continuous Autonomous Learning Pipeline/i)).toBeDefined()
      expect(screen.getByText(/Step 1: Observation Stream/i)).toBeDefined()
    })
  })

  it('allows toggling an active system directive', async () => {
    render(
      <SelfImprovementHubModal
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
      />
    )

    // Navigate to directives tab
    const tab3Btn = screen.getByRole('button', { name: /Evolved System Directives/i })
    fireEvent.click(tab3Btn)

    await waitFor(() => {
      expect(screen.getByText(/Preemptive Session Isolation Directive/i)).toBeDefined()
    })

    const toggleBtn = screen.getByRole('button', { name: /Active in Prompt/i })
    fireEvent.click(toggleBtn)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Paused/i })).toBeDefined()
    })
  })

  it('triggers a self-improvement cycle and calls onRefreshReport', async () => {
    const onRefresh = vi.fn()
    render(
      <SelfImprovementHubModal
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
        onRefreshReport={onRefresh}
      />
    )

    const triggerBtn = screen.getByRole('button', { name: /Trigger Self-Improvement Cycle/i })
    fireEvent.click(triggerBtn)

    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled()
    })
  })

  it('renders the adaptive score pill in TopHeader and fires onOpenImprovementHub', () => {
    const onOpen = vi.fn()
    render(
      <TopHeader
        connectionState="connected"
        transportType="websocket"
        adaptiveScore={94.8}
        onOpenImprovementHub={onOpen}
        onOpenSettings={vi.fn()}
      />
    )

    const pill = screen.getByTestId('header-adaptive-pill')
    expect(pill).toBeDefined()
    expect(pill.textContent).toContain('94.8% Adaptive')

    fireEvent.click(pill)
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('renders the Adaptive AI quick-action chip in RightSidebar and fires onOpenImprovementHub', () => {
    const onOpen = vi.fn()
    render(
      <RightSidebar
        isOpen={true}
        transportType="websocket"
        connectionState="connected"
        onSelectPrompt={vi.fn()}
        onOpenImprovementHub={onOpen}
      />
    )

    const chip = screen.getByTestId('hub-chip-improvements')
    expect(chip).toBeDefined()
    expect(chip.textContent).toContain('Adaptive AI')

    fireEvent.click(chip)
    expect(onOpen).toHaveBeenCalledTimes(1)
  })
})
