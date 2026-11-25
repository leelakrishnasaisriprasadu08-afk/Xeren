import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PlanApprovalCard } from '../components/Conversation/PlanApprovalCard'
import { MarkdownMessageView } from '../components/Conversation/MarkdownMessageView'
import { Conversation } from '../components/Conversation/Conversation'
import { MainWorkspace } from '../components/MainWorkspace/MainWorkspace'
import type { Message } from '../types/conversation'

describe('Plan Staging, "Proceed to the Plan" & Rich Chat Markdown Systems', () => {
  const samplePlan = {
    plan_id: 'plan_test_001',
    goal: 'Build an automated price alert script',
    risk_level: 'medium',
    steps: [
      { id: 1, description: 'Analyze requirements and data sources', status: 'completed' as const },
      { id: 2, description: 'Scrape graphics card pricing securely', action_type: 'automation', status: 'pending' as const },
      { id: 3, description: 'Deploy notification dispatch pipeline', tool: 'notification_dispatcher', status: 'pending' as const },
    ],
  }

  describe('PlanApprovalCard Component', () => {
    it('renders goal, steps, risk level, and strict safety policy banner', () => {
      render(<PlanApprovalCard plan={samplePlan} />)

      expect(screen.getByTestId('plan-approval-card')).toBeInTheDocument()
      expect(screen.getByText('Build an automated price alert script')).toBeInTheDocument()
      expect(screen.getByTestId('plan-risk-tag')).toHaveTextContent('medium risk')
      expect(screen.getAllByTestId('plan-step-item').length).toBe(3)
      expect(screen.getByText(/Strict plan-first gating/i)).toBeInTheDocument()
      expect(screen.getByTestId('plan-proceed-btn')).toBeInTheDocument()
    })

    it('clicking Proceed to the Plan button fires onProceed with proceed to the plan prompt and transitions to executing', () => {
      const onProceedMock = vi.fn()
      render(<PlanApprovalCard plan={samplePlan} onProceed={onProceedMock} />)

      const proceedBtn = screen.getByTestId('plan-proceed-btn')
      fireEvent.click(proceedBtn)

      expect(onProceedMock).toHaveBeenCalledWith('proceed to the plan')
      expect(screen.getByTestId('plan-executing-indicator')).toBeInTheDocument()
      expect(screen.getByText(/Executing Autonomous Plan/i)).toBeInTheDocument()
    })
  })

  describe('MarkdownMessageView Component', () => {
    it('renders code blocks with language badge and functioning copy code button', async () => {
      const markdownCode = 'Here is the implementation:\n\n```python\nimport xeren\nprint("Xeren Active")\n```'

      // Mock clipboard writeText
      const writeTextMock = vi.fn().mockResolvedValue(undefined)
      Object.assign(navigator, {
        clipboard: { writeText: writeTextMock },
      })

      render(<MarkdownMessageView content={markdownCode} />)

      expect(screen.getByTestId('code-block')).toBeInTheDocument()
      expect(screen.getByText('python')).toBeInTheDocument()
      expect(screen.getByText(/print\("Xeren Active"\)/)).toBeInTheDocument()

      const copyBtn = screen.getByTestId('copy-code-btn')
      expect(copyBtn).toHaveTextContent('Copy')

      await act(async () => {
        fireEvent.click(copyBtn)
      })
      expect(writeTextMock).toHaveBeenCalledWith('import xeren\nprint("Xeren Active")')
      await waitFor(() => {
        expect(copyBtn).toHaveTextContent('Copied!')
      })
    })

    it('detects staged plan in metadata and renders PlanApprovalCard', () => {
      const onProceedMock = vi.fn()
      render(
        <MarkdownMessageView
          content="I have analyzed your request and prepared the plan."
          metadata={{
            plan: samplePlan,
            planStaged: true,
          }}
          onProceedPlan={onProceedMock}
        />
      )

      expect(screen.getByTestId('plan-approval-card')).toBeInTheDocument()
      const proceedBtn = screen.getByTestId('plan-proceed-btn')
      fireEvent.click(proceedBtn)
      expect(onProceedMock).toHaveBeenCalledWith('proceed to the plan')
    })

    it('renders research verification box and permitted data badges when present in metadata', () => {
      render(
        <MarkdownMessageView
          content="Grounded facts verified with domain authority."
          metadata={{
            research: {
              citations: [
                { title: 'Official Documentation', url: 'https://docs.xeren.ai' },
              ],
            },
            heldDataApplied: ['local_database.sqlite', 'user_notes.txt'],
          }}
        />
      )

      expect(screen.getByTestId('research-verification-box')).toBeInTheDocument()
      expect(screen.getByText(/Verified Truth Matrix/i)).toBeInTheDocument()

      // Expand research citations
      fireEvent.click(screen.getByRole('button', { name: /Verified Truth Matrix/i }))
      expect(screen.getByText('Official Documentation')).toBeInTheDocument()

      // Permitted data badges
      expect(screen.getByTestId('held-data-badges')).toBeInTheDocument()
      expect(screen.getByText(/local_database.sqlite/)).toBeInTheDocument()
      expect(screen.getByText(/user_notes.txt/)).toBeInTheDocument()
    })
  })

  describe('Conversation & MainWorkspace Integration', () => {
    it('renders staged plan in Conversation and provides one-click proceed approval', () => {
      const onProceedMock = vi.fn()
      const messages: Message[] = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Deploy the automated trading monitor',
          timestamp: Date.now() - 5000,
        },
        {
          id: 'msg-2',
          role: 'xeren',
          content: 'Here is the staged plan before proceeding:',
          timestamp: Date.now(),
          metadata: {
            plan: samplePlan,
            planStaged: true,
          },
        },
      ]

      render(
        <Conversation
          messages={messages}
          onProceedPlan={onProceedMock}
        />
      )

      expect(screen.getByTestId('message-row-user')).toBeInTheDocument()
      expect(screen.getByTestId('message-row-xeren')).toBeInTheDocument()
      expect(screen.getByTestId('plan-approval-card')).toBeInTheDocument()

      fireEvent.click(screen.getByTestId('plan-proceed-btn'))
      expect(onProceedMock).toHaveBeenCalledWith('proceed to the plan')
    })

    it('renders docked active-staged-plan-dock-pill in MainWorkspace when a plan is waiting for approval', () => {
      const onProceedMock = vi.fn()
      const messages: Message[] = [
        {
          id: 'msg-1',
          role: 'xeren',
          content: 'Staged plan ready.',
          timestamp: Date.now(),
          metadata: {
            plan: samplePlan,
            planStaged: true,
          },
        },
      ]

      render(
        <MainWorkspace
          presenceState="idle"
          activeAmplitude={0}
          prefersReducedMotion={false}
          messages={messages}
          currentStreamingText=""
          currentStreamingId={null}
          agentProgress={null}
          activeMilestone={null}
          isListening={false}
          isSpeaking={false}
          onSendMessage={vi.fn()}
          onProceedPlan={onProceedMock}
          onStartListening={vi.fn()}
          onStopListening={vi.fn()}
          onInterrupt={vi.fn()}
        />
      )

      const dockPill = screen.getByTestId('active-staged-plan-dock-pill')
      expect(dockPill).toBeInTheDocument()
      expect(screen.getByText('Plan Waiting for Approval:')).toBeInTheDocument()

      const dockProceedBtn = screen.getByTestId('dock-pill-proceed-btn')
      fireEvent.click(dockProceedBtn)
      expect(onProceedMock).toHaveBeenCalledWith('proceed to the plan')
    })
  })
})
