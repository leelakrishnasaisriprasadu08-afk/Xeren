import { describe, it, expect, vi, beforeEach, afterAll } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { ConnectedAppsModal } from '../components/ConnectedAppsModal/ConnectedAppsModal'
import { App } from '../App'

describe('Connected Apps & MCP Server Interoperability Tests', () => {
  const originalFetch = window.fetch

  beforeEach(() => {
    vi.clearAllMocks()
    window.fetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/call-tool')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ output: { status: 'mock_executed' } }),
        } as unknown as Response)
      }
      if (typeof url === 'string' && url.includes('/pipelines/execute')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            pipeline_id: 'github-to-code-to-slack',
            success: true,
            step_results: [
              {
                step_id: 'step-1',
                server_id: 'github',
                tool_name: 'list_issues',
                description: '1. Fetch latest open bug report from GitHub',
                success: true,
                latency_ms: 12,
                output: { issues: [{ id: 101, title: 'Bug report' }] },
              },
            ],
            final_output: { status: 'success' },
            execution_time_ms: 24,
          }),
        } as unknown as Response)
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ success: true }),
      } as unknown as Response)
    })
  })

  afterAll(() => {
    window.fetch = originalFetch
  })

  it('renders ConnectedAppsModal with all 4 tabs and server cards', () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} />)

    expect(screen.getByTestId('connected-apps-modal')).toBeInTheDocument()
    expect(screen.getByText('Connected Apps & MCP Hub')).toBeInTheDocument()

    // 4 Tabs
    expect(screen.getByTestId('tab-connected-apps')).toBeInTheDocument()
    expect(screen.getByTestId('tab-app-catalog')).toBeInTheDocument()
    expect(screen.getByTestId('tab-workflows')).toBeInTheDocument()
    expect(screen.getByTestId('tab-custom-server')).toBeInTheDocument()

    // Server cards present
    expect(screen.getByTestId('server-card-filesystem')).toBeInTheDocument()
    expect(screen.getByTestId('server-card-github')).toBeInTheDocument()
    expect(screen.getByTestId('server-card-sqlite')).toBeInTheDocument()
  })

  it('toggles server enabled status and expands tools with live tool testing', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} />)

    // 1. Toggle server active switch
    const toggleBtn = screen.getByTestId('toggle-server-filesystem')
    expect(toggleBtn).toHaveClass('active')

    fireEvent.click(toggleBtn)
    expect(toggleBtn).not.toHaveClass('active')

    // Re-enable
    fireEvent.click(toggleBtn)
    expect(toggleBtn).toHaveClass('active')

    // 2. Expand tools for filesystem
    const expandBtn = screen.getAllByText(/View 3 Tools ▼/i)[0]
    fireEvent.click(expandBtn)

    expect(screen.getByTestId('tools-list-filesystem')).toBeInTheDocument()
    expect(screen.getByText('read_file')).toBeInTheDocument()
    expect(screen.getByText('write_file')).toBeInTheDocument()

    // 3. Click Test Tool
    const testBtn = screen.getByTestId('test-tool-read_file')
    await act(async () => {
      fireEvent.click(testBtn)
    })

    expect(await screen.findByTestId('tool-execution-result')).toBeInTheDocument()
  })

  it('allows connecting an app preset from the App Catalog', () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} />)

    // Switch to Catalog
    fireEvent.click(screen.getByTestId('tab-app-catalog'))
    expect(screen.getByText('Popular App & Service Connectors')).toBeInTheDocument()

    // Find Docker preset and connect
    const connectDockerBtn = screen.getByTestId('connect-preset-docker')
    fireEvent.click(connectDockerBtn)

    // After connecting, switches back to Connected tab with Docker active
    expect(screen.getByTestId('tab-connected-apps')).toHaveClass('active')
    expect(screen.getByTestId('server-card-docker')).toBeInTheDocument()
  })

  it('registers a custom MCP server via the custom form', () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} />)

    // Switch to Custom MCP tab
    fireEvent.click(screen.getByTestId('tab-custom-server'))
    expect(screen.getByText('Connect Custom MCP Server')).toBeInTheDocument()

    // Fill form
    const nameInput = screen.getByLabelText(/Server \/ Application Name/i)
    const cmdInput = screen.getByLabelText(/Command/i)

    fireEvent.change(nameInput, { target: { value: 'Linear Tracker' } })
    fireEvent.change(cmdInput, { target: { value: 'npx' } })

    const submitBtn = screen.getByTestId('submit-custom-mcp-btn')
    fireEvent.click(submitBtn)

    // Automatically redirects to Connected tab with new server present
    expect(screen.getByTestId('tab-connected-apps')).toHaveClass('active')
    expect(screen.getByText('Linear Tracker')).toBeInTheDocument()
  })

  it('executes cross-app interoperability workflow where apps work together', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} />)

    // Switch to Work Together tab
    fireEvent.click(screen.getByTestId('tab-workflows'))
    expect(screen.getByText('Cross-App Collaboration Engine')).toBeInTheDocument()

    // Visual flow nodes exist
    expect(screen.getByTestId('flow-node-step-1')).toBeInTheDocument()
    expect(screen.getByTestId('flow-node-step-2')).toBeInTheDocument()
    expect(screen.getByTestId('flow-node-step-3')).toBeInTheDocument()
    expect(screen.getByTestId('flow-node-step-4')).toBeInTheDocument()

    // Run Cross-App Workflow
    const runWorkflowBtn = screen.getByTestId('execute-cross-app-btn')
    await act(async () => {
      fireEvent.click(runWorkflowBtn)
    })

    // Results rendered
    expect(await screen.findByTestId('pipeline-execution-result')).toBeInTheDocument()
    expect(screen.getByText(/Cross-App Interoperability Succeeded/i)).toBeInTheDocument()
  })

  it('TopHeader Apps pill and Bottom-Right speed-dial chip trigger ConnectedAppsModal', () => {
    render(<App />)

    // 1. TopHeader Apps button
    const headerAppsBtn = screen.getByTestId('header-apps-btn')
    expect(headerAppsBtn).toBeInTheDocument()

    fireEvent.click(headerAppsBtn)
    expect(screen.getByTestId('connected-apps-modal')).toBeInTheDocument()

    // Close modal
    fireEvent.click(screen.getByTestId('close-apps-modal-btn'))
    expect(screen.queryByTestId('connected-apps-modal')).not.toBeInTheDocument()

    // 2. Bottom-Right floating trigger opens speed-dial chart
    const floatingHubBtn = screen.getByTestId('floating-hub-trigger')
    fireEvent.click(floatingHubBtn)

    // Speed-dial chip for Apps
    const appsChip = screen.getByTestId('hub-chip-apps')
    expect(appsChip).toBeInTheDocument()

    fireEvent.click(appsChip)
    expect(screen.getByTestId('connected-apps-modal')).toBeInTheDocument()
  })
})
