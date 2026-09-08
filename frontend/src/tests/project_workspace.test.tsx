import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ProjectWorkspaceModal } from '../components/ProjectWorkspaceModal/ProjectWorkspaceModal'
import { TopHeader } from '../components/TopHeader/TopHeader'
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
    {
      user_id: 'usr_peer_02',
      handle: '@sarah_ai',
      display_name: 'Dr. Sarah Chen',
      email: 'sarah.chen@deepmind-labs.org',
      role: 'ai_specialist',
      joined_at: '2026-09-07T12:00:00Z',
      is_owner: false,
      active_task: 'Fine-tuning prompt reasoning templates',
    },
  ],
  invites: [],
  specifications: {
    tech_stack: ['TypeScript', 'FastAPI', 'MongoDB Atlas', 'React 19', 'WebSockets'],
    architecture_pattern: 'Distributed Multi-Agent Event Bus',
    constraints: [
      'Zero-interruption workstation isolation',
      'Strict role-based action gating',
      'Real-time sync latency < 50ms',
    ],
    target_apis: ['OpenAI API', 'Anthropic Claude API', 'Gemini Pro API', 'MongoDB Atlas'],
    deliverables: [
      'Parallel collaborative workstations',
      'AI Coach integration',
      'Role matrix management',
    ],
  },
  milestones: [
    {
      milestone_id: 'ms_grp_01',
      title: 'Real-time Workstation Event Bus',
      description: 'Deploy WebSocket multiplexer for zero-lag peer collaboration',
      assigned_role: 'architect',
      assigned_member_handle: '@xeren_dev',
      status: 'completed',
    },
    {
      milestone_id: 'ms_grp_02',
      title: 'Multi-Model Reasoning Benchmarks',
      description: 'Benchmark Claude 3.5 Sonnet vs Gemini 2.0 Flash for sub-agents',
      assigned_role: 'ai_specialist',
      assigned_member_handle: '@sarah_ai',
      status: 'in_progress',
    },
  ],
  tags: ['team', 'collaboration', 'neural', 'sync'],
  synced_with_mongo: true,
}

describe('Project Workspace, Dedicated AI Coach, and Workstation Isolation', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
    // Global fetch mock
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/coach/messages')) {
        const isSarah = url.includes('member_id=usr_peer_02')
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              messages: [
                {
                  message_id: isSarah ? 'pcm_sarah_01' : 'pcm_dev_01',
                  project_id: 'proj_cyberforge_group',
                  member_user_id: isSarah ? 'usr_peer_02' : 'usr_dev_01',
                  member_handle: isSarah ? '@sarah_ai' : '@xeren_dev',
                  sender: 'coach_agent',
                  content: isSarah
                    ? 'Welcome Dr. Chen! Ready to mentor on AI models.'
                    : 'Welcome Lead Architect! Event-driven modular architecture loaded.',
                  timestamp: new Date().toISOString(),
                  role_context: isSarah ? 'AI Specialist' : 'System Architect',
                },
              ],
            }),
        })
      }
      if (url.includes('/coach/chat')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              message: {
                message_id: `pcm_reply_${Date.now()}`,
                project_id: 'proj_cyberforge_group',
                member_user_id: 'usr_dev_01',
                member_handle: '@xeren_dev',
                sender: 'coach_agent',
                content: '### [Architecture Guidance for Architect]\n\nDecoupled event streams are active.',
                timestamp: new Date().toISOString(),
                role_context: 'System Architect',
              },
            }),
        })
      }
      if (url.includes('/specifications')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              project: mockProject,
            }),
        })
      }
      if (url.includes('/members/') && url.includes('/role')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              project: mockProject,
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      })
    })
  })

  it('renders ProjectWorkspaceModal with title, type, and active tabs', async () => {
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        currentUserId="usr_dev_01"
      />
    )

    expect(screen.getByText('CyberForge AI Engine')).toBeInTheDocument()
    expect(screen.getByText('👥 Group Project')).toBeInTheDocument()
    expect(screen.getByText('🍃 Atlas Synced')).toBeInTheDocument()
    expect(screen.getByText('Zero-Interruption Parallel Stream')).toBeInTheDocument()

    // Tabs
    expect(screen.getByText(/AI Coach Workstation/i)).toBeInTheDocument()
    expect(screen.getByText(/Project Specifications/i)).toBeInTheDocument()
    expect(screen.getByText(/Roles & Teammates/i)).toBeInTheDocument()
    expect(screen.getByText(/Milestones & Sprints/i)).toBeInTheDocument()
  })

  it('displays teammate workstation switcher and active workstation indicators', async () => {
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        currentUserId="usr_dev_01"
      />
    )

    // Member pills
    expect(screen.getByRole('button', { name: /@xeren_dev/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /@sarah_ai/i })).toBeInTheDocument()
    expect(screen.getByText('(You)')).toBeInTheDocument()

    // Active task
    expect(screen.getByText(/Designing zero-interruption workstation pipelines/i)).toBeInTheDocument()
  })

  it('interacts with AI Coach Agent in isolated workstation stream', async () => {
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        currentUserId="usr_dev_01"
      />
    )

    // Verify initial coach message rendered
    await waitFor(() => {
      expect(
        screen.getByText(/Event-driven modular architecture loaded/i)
      ).toBeInTheDocument()
    })

    // Input question
    const textarea = screen.getByPlaceholderText(/Ask Project Coach a question or doubt/i)
    fireEvent.change(textarea, { target: { value: 'How should I structure the WebSocket event bus?' } })

    const sendBtn = screen.getByRole('button', { name: /Consult Coach/i })
    fireEvent.click(sendBtn)

    // User question appears
    expect(screen.getByText('How should I structure the WebSocket event bus?')).toBeInTheDocument()

    // Coach response appears
    await waitFor(() => {
      expect(screen.getByText(/Decoupled event streams are active/i)).toBeInTheDocument()
    })
  })

  it('switches to peer workstation (@sarah_ai) and loads isolated session history', async () => {
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        currentUserId="usr_dev_01"
      />
    )

    // Click on Sarah's workstation tab
    const sarahTab = screen.getByRole('button', { name: /@sarah_ai/i })
    fireEvent.click(sarahTab)

    // Sarah's coach stream should be loaded
    await waitFor(() => {
      expect(screen.getByText(/Ready to mentor on AI models/i)).toBeInTheDocument()
    })
  })

  it('switches to Specifications tab, displays specifications, and saves updates', async () => {
    const onProjectUpdated = vi.fn()
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        currentUserId="usr_dev_01"
        onProjectUpdated={onProjectUpdated}
      />
    )

    // Click Specifications tab
    fireEvent.click(screen.getByRole('button', { name: /Project Specifications/i }))

    expect(screen.getByText('🛠️ Technology Stack')).toBeInTheDocument()
    expect(screen.getByText('🏛️ Architecture Pattern')).toBeInTheDocument()
    expect(screen.getByText('🔒 Constraints & Security Rules')).toBeInTheDocument()

    const saveBtn = screen.getByRole('button', { name: /Save Technical Specifications/i })
    expect(saveBtn).toBeInTheDocument()
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(screen.getByText(/Specifications successfully updated!/i)).toBeInTheDocument()
    })
  })

  it('switches to Roles tab and displays member role matrix', async () => {
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        currentUserId="usr_dev_01"
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /Roles & Teammates/i }))

    expect(screen.getByText('Role Matrix & Member Responsibilities')).toBeInTheDocument()
    expect(screen.getByText('Alex Mercer')).toBeInTheDocument()
    expect(screen.getByText('Dr. Sarah Chen')).toBeInTheDocument()
    expect(screen.getAllByText(/Workstation Isolated • No Message Bleeding/i)).toHaveLength(2)
  })

  it('switches to Milestones tab and displays progress and deliverables', async () => {
    render(
      <ProjectWorkspaceModal
        isOpen={true}
        onClose={vi.fn()}
        project={mockProject}
        currentUserId="usr_dev_01"
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /Milestones & Sprints/i }))

    expect(screen.getByText('Sprint Delivery Progress')).toBeInTheDocument()
    expect(screen.getByText('50% Completed')).toBeInTheDocument()
    expect(screen.getByText('Real-time Workstation Event Bus')).toBeInTheDocument()
    expect(screen.getByText('Multi-Model Reasoning Benchmarks')).toBeInTheDocument()
  })

  it('TopHeader renders active project workspace button and triggers click', async () => {
    const onOpenProjectWorkspace = vi.fn()
    render(
      <TopHeader
        connectionState="connected"
        transportType="websocket"
        activeProjectName="CyberForge AI Engine"
        onOpenProjectWorkspace={onOpenProjectWorkspace}
        onOpenSettings={vi.fn()}
      />
    )

    const projectBtn = screen.getByTestId('header-active-project-btn')
    expect(projectBtn).toBeInTheDocument()
    expect(projectBtn).toHaveTextContent('CyberForge AI Engine')
    expect(projectBtn).toHaveTextContent('Coach')

    fireEvent.click(projectBtn)
    expect(onOpenProjectWorkspace).toHaveBeenCalledTimes(1)
  })
})
