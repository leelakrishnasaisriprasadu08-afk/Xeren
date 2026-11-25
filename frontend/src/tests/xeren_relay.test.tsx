import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { XerenRelay } from '../components/XerenRelay/XerenRelay'
import { ProjectWorkspaceModal } from '../components/ProjectWorkspaceModal/ProjectWorkspaceModal'
import type { Project } from '../types/project'

const mockProject: Project = {
  project_id: 'proj_cyberforge_group',
  name: 'CyberForge AI Engine',
  description: 'Collaborative team project for multi-model autonomous agent development and distributed deployment.',
  project_type: 'group',
  owner_id: 'usr_dev_01',
  owner_name: 'Alex Mercer',
  owner_handle: '@xeren_dev',
  created_at: '2026-09-07T12:00:00Z',
  updated_at: '2026-09-07T12:00:00Z',
  members: [
    {
      user_id: 'usr_dev_01',
      handle: '@xeren_dev',
      display_name: 'Alex Mercer',
      email: 'alex.mercer@xeren.ai',
      role: 'architect',
      joined_at: '2026-09-07T12:00:00Z',
      is_owner: true,
      active_task: 'Designing zero-interruption workstation pipelines',
    },
  ],
  invites: [],
  specifications: {
    tech_stack: ['TypeScript', 'FastAPI'],
    architecture_pattern: 'Distributed Event Bus',
    constraints: ['Workstation isolation'],
    target_apis: ['OpenAI API'],
    deliverables: ['Autonomous Relay engine'],
  },
  milestones: [],
  tags: ['team', 'relay'],
  synced_with_mongo: true,
}

describe('Xeren Relay - Autonomous Background Execution & Connected Apps Hub', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  it('renders Xeren Relay with title, metrics, and operations grid', () => {
    render(<XerenRelay projectId="proj_test" projectName="CyberForge AI Engine" />)

    // Check title
    expect(screen.getByText('Xeren')).toBeInTheDocument()
    expect(screen.getByText('Relay')).toBeInTheDocument()
    expect(screen.getByText(/AUTONOMOUS BACKGROUND ENGINE/i)).toBeInTheDocument()

    // Check metric cards
    expect(screen.getByTestId('metric-active-workers')).toBeInTheDocument()
    expect(screen.getByTestId('metric-completed-jobs')).toBeInTheDocument()
    expect(screen.getByTestId('metric-connected-apps')).toBeInTheDocument()

    // Check 3 live operations cards
    expect(screen.getByTestId('github-relay-card')).toBeInTheDocument()
    expect(screen.getByTestId('chatgpt-relay-card')).toBeInTheDocument()
    expect(screen.getByTestId('quota-relay-card')).toBeInTheDocument()
  })

  it('displays live GitHub push file progress counter and percentage', () => {
    render(<XerenRelay />)

    // Default upload state: 18 of 24 files uploaded (75%)
    const filesCount = screen.getByTestId('github-files-count')
    expect(filesCount).toHaveTextContent('18')
    expect(filesCount).toHaveTextContent('24')

    const percentText = screen.getByTestId('github-upload-percent')
    expect(percentText).toHaveTextContent('75%')

    const progressBar = screen.getByTestId('github-progress-bar')
    expect(progressBar).toHaveStyle({ width: '75%' })

    // Simulate clicking push button
    const pushBtn = screen.getByTestId('btn-simulate-git-push')
    fireEvent.click(pushBtn)

    expect(screen.getByTestId('relay-alert-banner')).toBeInTheDocument()
  })

  it('displays ChatGPT / DALL-E generation status and completion asset', () => {
    render(<XerenRelay />)

    const stepLabel = screen.getByTestId('image-gen-step')
    expect(stepLabel).toHaveTextContent(/Diffusion step 44\/50/i)

    const percentLabel = screen.getByTestId('image-gen-percent')
    expect(percentLabel).toHaveTextContent('88%')

    const triggerBtn = screen.getByTestId('btn-simulate-image-gen')
    fireEvent.click(triggerBtn)

    expect(screen.getByTestId('relay-alert-banner')).toBeInTheDocument()
    expect(screen.getByText(/Image generation started/i)).toBeInTheDocument()
  })

  it('displays model rate-limit cooldown banner with 10:00 AM reset indicator', () => {
    render(<XerenRelay />)

    const cooldownBox = screen.getByTestId('cooldown-box')
    expect(cooldownBox).toBeInTheDocument()
    expect(within(cooldownBox).getByText(/Hourly Quota Reached/i)).toBeInTheDocument()
    expect(within(cooldownBox).getByText(/10:00 AM/i)).toBeInTheDocument()
    const quotaCard = screen.getByTestId('quota-relay-card')
    expect(within(quotaCard).getByText('48')).toBeInTheDocument()
  })

  it('lists connected apps with permission scopes and toggles authorization', () => {
    render(<XerenRelay />)

    const permissionsBox = screen.getByTestId('apps-permissions-box')
    expect(permissionsBox).toBeInTheDocument()

    // Apps present
    expect(screen.getByText('GitHub Enterprise')).toBeInTheDocument()
    expect(screen.getByText('ChatGPT / DALL-E 3')).toBeInTheDocument()
    expect(screen.getByText('Figma Tokens API')).toBeInTheDocument()
    expect(screen.getByText('Sandboxed Cloud Runtime')).toBeInTheDocument()

    // Scopes chips
    expect(screen.getByText('repo:write')).toBeInTheDocument()
    expect(screen.getByText('model:generate')).toBeInTheDocument()

    // Toggle disconnect / authorize
    const toggleBtn = screen.getByTestId('toggle-app-app_github')
    expect(toggleBtn).toHaveTextContent('Disconnect')

    fireEvent.click(toggleBtn)
    expect(toggleBtn).toHaveTextContent('Authorize')
  })

  it('filters background tasks by status: all, in_progress, completed, queued', () => {
    render(<XerenRelay />)

    expect(screen.getByTestId('task-card-TASK-RELAY-1049')).toBeInTheDocument()
    expect(screen.getByTestId('task-card-TASK-RELAY-1048')).toBeInTheDocument()
    expect(screen.getByTestId('task-card-TASK-RELAY-1050')).toBeInTheDocument()

    // Filter to Completed
    fireEvent.click(screen.getByTestId('filter-completed'))
    expect(screen.getByTestId('task-card-TASK-RELAY-1048')).toBeInTheDocument()
    expect(screen.queryByTestId('task-card-TASK-RELAY-1049')).not.toBeInTheDocument()

    // Filter to Queued
    fireEvent.click(screen.getByTestId('filter-queued'))
    expect(screen.getByTestId('task-card-TASK-RELAY-1050')).toBeInTheDocument()
    expect(screen.queryByTestId('task-card-TASK-RELAY-1048')).not.toBeInTheDocument()

    // Filter back to All
    fireEvent.click(screen.getByTestId('filter-all'))
    expect(screen.getByTestId('task-card-TASK-RELAY-1049')).toBeInTheDocument()
  })

  it('expands comprehensive Work Report with duration, files, and verification audit', () => {
    render(<XerenRelay />)

    // TASK-RELAY-1049 is expanded by default
    const workReport = screen.getByTestId('work-report-TASK-RELAY-1049')
    expect(workReport).toBeInTheDocument()
    expect(within(workReport).getByText(/Work Report & Telemetry Verification/i)).toBeInTheDocument()
    expect(within(workReport).getByText(/All pre-push git hooks verified clean/i)).toBeInTheDocument()
    expect(within(workReport).getByText(/src\/components\/XerenRelay\/XerenRelay.tsx/i)).toBeInTheDocument()
  })

  it('allows assigning a new background task to Xeren Relay', () => {
    render(<XerenRelay />)

    const input = screen.getByTestId('input-new-task-title')
    fireEvent.change(input, { target: { value: 'Deploy Canary Build to Staging' } })

    const submitBtn = screen.getByTestId('btn-dispatch-task')
    expect(submitBtn).not.toBeDisabled()

    fireEvent.click(submitBtn)

    expect(screen.getByText('Deploy Canary Build to Staging')).toBeInTheDocument()
    expect(screen.getByTestId('relay-alert-banner')).toHaveTextContent(/Deploy Canary Build to Staging/i)
  })

  it('seamlessly integrates into ProjectWorkspaceModal under the Xeren Relay tab', () => {
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        initialTab="relay"
      />
    )

    // Verify Relay tab button is rendered and active
    const relayTabBtn = screen.getByTestId('tab-btn-relay')
    expect(relayTabBtn).toHaveClass('active')

    // Verify Xeren Relay view is mounted inside the modal
    expect(screen.getByTestId('project-relay-panel')).toBeInTheDocument()
    expect(screen.getByTestId('xeren-relay-container')).toBeInTheDocument()
  })
})
