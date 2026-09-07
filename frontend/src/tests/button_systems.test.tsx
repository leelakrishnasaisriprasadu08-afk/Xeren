import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'
import { MessageComposer } from '../components/MessageComposer/MessageComposer'
import { NotificationsDrawer, type SystemNotification } from '../components/NotificationsDrawer/NotificationsDrawer'
import { PluginManagerModal } from '../components/PluginManagerModal/PluginManagerModal'
import { KnowledgeVaultModal } from '../components/KnowledgeVaultModal/KnowledgeVaultModal'
import { RightSidebar } from '../components/RightSidebar/RightSidebar'

describe('Xeren Interactive Button Systems & Modals Verification', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  // 1. Notification Drawer Functionality
  it('renders NotificationsDrawer with notifications, mark read, and clear actions', () => {
    const mockNotifications: SystemNotification[] = [
      {
        id: 'n1',
        timestamp: '1m ago',
        title: 'Security Gate Alert',
        message: 'AES-256-GCM hardware crypto initialized',
        type: 'security',
        read: false,
      },
      {
        id: 'n2',
        timestamp: '5m ago',
        title: 'Fiverr Order',
        message: 'Order FIVERR-9821 brief parsed',
        type: 'order',
        read: true,
      },
    ]

    const onMarkAllRead = vi.fn()
    const onClearAll = vi.fn()
    const onDismiss = vi.fn()

    render(
      <NotificationsDrawer
        isOpen={true}
        onClose={vi.fn()}
        notifications={mockNotifications}
        onMarkAllRead={onMarkAllRead}
        onClearAll={onClearAll}
        onDismiss={onDismiss}
      />
    )

    expect(screen.getByText('Activity Center')).toBeInTheDocument()
    expect(screen.getByTestId('unread-count-badge')).toHaveTextContent('1 new')
    expect(screen.getByText('Security Gate Alert')).toBeInTheDocument()
    expect(screen.getByText('Fiverr Order')).toBeInTheDocument()

    // Test Mark All Read button
    fireEvent.click(screen.getByTestId('mark-all-read-btn'))
    expect(onMarkAllRead).toHaveBeenCalledTimes(1)

    // Test Clear All button
    fireEvent.click(screen.getByTestId('clear-all-notif-btn'))
    expect(onClearAll).toHaveBeenCalledTimes(1)
  })

  // 2. MessageComposer 3-Tier Security File Ingestion
  it('attaches files and categorizes into Liberal, Sensitive, and More Sensitive tiers', () => {
    const onSendMessage = vi.fn()

    render(
      <MessageComposer
        presenceState="idle"
        isListening={false}
        isSpeaking={false}
        activeMode="think"
        onSendMessage={onSendMessage}
        onStartListening={vi.fn()}
        onStopListening={vi.fn()}
        onInterrupt={vi.fn()}
      />
    )

    const fileInput = screen.getByTestId('file-upload-input')

    // Simulate uploading 3 files of different security tiers
    const liberalFile = new File(['content'], 'notes.txt', { type: 'text/plain' })
    const sensitiveFile = new File(['content'], 'financial_report.pdf', { type: 'application/pdf' })
    const moreSensitiveFile = new File(['content'], 'user_aadhar_card.pdf', { type: 'application/pdf' })

    fireEvent.change(fileInput, {
      target: { files: [liberalFile, sensitiveFile, moreSensitiveFile] },
    })

    // Chips appear with appropriate security tier badges
    expect(screen.getByTestId('attachments-tray')).toBeInTheDocument()
    expect(screen.getByTestId('attachment-chip-notes.txt')).toHaveTextContent('Liberal')
    expect(screen.getByTestId('attachment-chip-financial_report.pdf')).toHaveTextContent('Sensitive')
    expect(screen.getByTestId('attachment-chip-user_aadhar_card.pdf')).toHaveTextContent('More Sensitive')

    // More Sensitive warning banner renders
    expect(screen.getByTestId('more-sensitive-alert')).toBeInTheDocument()

    // Send message includes attachment tags
    fireEvent.click(screen.getByTestId('send-message-button'))
    expect(onSendMessage).toHaveBeenCalledWith(
      expect.stringContaining('[Attachment: user_aadhar_card.pdf (More Sensitive Tier)]')
    )
  })

  // 3. Plugin Manager Modal
  it('renders PluginManagerModal and allows toggling plugin active state', () => {
    const onClose = vi.fn()
    render(<PluginManagerModal isOpen={true} onClose={onClose} />)

    expect(screen.getByText('Autonomous Plugin Registry')).toBeInTheDocument()
    expect(screen.getByText('Strawberry AI Research')).toBeInTheDocument()
    expect(screen.getByText('8-Layer Security Gate')).toBeInTheDocument()

    const strawberryToggle = screen.getByTestId('toggle-plugin-strawberry_research')
    expect(strawberryToggle).toHaveTextContent('Active')

    // Toggle plugin
    fireEvent.click(strawberryToggle)
    expect(strawberryToggle).toHaveTextContent('Disabled')

    // Close modal
    fireEvent.click(screen.getByTestId('close-plugin-modal-btn'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  // 4. Knowledge Vault & Qdrant RAG Modal
  it('renders KnowledgeVaultModal with Qdrant vector store telemetry and query test', async () => {
    const onClose = vi.fn()
    render(<KnowledgeVaultModal isOpen={true} onClose={onClose} />)

    expect(screen.getByText('Knowledge Vault & RAG Store')).toBeInTheDocument()
    expect(screen.getByText('Qdrant Local')).toBeInTheDocument()
    expect(screen.getByText('Cosine (0-1)')).toBeInTheDocument()

    // Test vector search query
    const input = screen.getByTestId('rag-search-input')
    fireEvent.change(input, { target: { value: 'AES hardware specs' } })
    fireEvent.click(screen.getByTestId('rag-search-submit'))

    act(() => {
      vi.advanceTimersByTime(500)
    })

    expect(screen.getByTestId('rag-search-results')).toHaveTextContent(/Top 3 Qdrant Chunks matched/i)
  })

  // 5. RightSidebar Diagnostics Ping
  it('RightSidebar Run Diagnostics button triggers latency check and shows result', async () => {
    // Mock window fetch for diagnostics
    const originalFetch = window.fetch
    window.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ storage: 'sqlite', status: 'healthy' }),
    } as unknown as Response)

    render(
      <RightSidebar
        isOpen={true}
        transportType="mock"
        connectionState="connected"
        onSelectPrompt={vi.fn()}
      />
    )

    const diagBtn = screen.getByTestId('run-diagnostics-btn')
    expect(diagBtn).toHaveTextContent('⚡ Run Diagnostics')

    await act(async () => {
      fireEvent.click(diagBtn)
    })

    expect(screen.getByTestId('diagnostics-result')).toHaveTextContent(/FastAPI live/i)
    window.fetch = originalFetch
  })

  // 6. Full App Integration: TopHeader Quick Action Buttons Trigger Modals
  it('clicking TopHeader notification bell opens drawer and clicking header plugins opens modal', () => {
    render(<App />)

    // 1. Notification bell
    const notifBtn = screen.getByTestId('header-notifications-btn')
    expect(screen.getByTestId('header-unread-count')).toHaveTextContent('3')

    fireEvent.click(notifBtn)
    expect(screen.getByTestId('notifications-panel')).toBeInTheDocument()

    // Close notification panel
    fireEvent.click(screen.getByTestId('close-notif-btn'))
    expect(screen.queryByTestId('notifications-panel')).not.toBeInTheDocument()

    // 2. Header Plugins quick action button
    const pluginsBtn = screen.getByTestId('header-plugins-btn')
    fireEvent.click(pluginsBtn)
    expect(screen.getByTestId('plugin-manager-modal')).toBeInTheDocument()

    // Close plugins modal
    fireEvent.click(screen.getByTestId('close-plugin-modal-btn'))
    expect(screen.queryByTestId('plugin-manager-modal')).not.toBeInTheDocument()

    // 3. Header Knowledge quick action button
    const knowledgeBtn = screen.getByTestId('header-knowledge-btn')
    fireEvent.click(knowledgeBtn)
    expect(screen.getByTestId('knowledge-vault-modal')).toBeInTheDocument()

    // Close knowledge modal
    fireEvent.click(screen.getByTestId('close-knowledge-modal-btn'))
    expect(screen.queryByTestId('knowledge-vault-modal')).not.toBeInTheDocument()
  })

  // 7. Cognitive Mode Buttons
  it('clicking Think/Reason/Create tabs switches active mode with tactile response', () => {
    render(<App />)

    const thinkTab = screen.getByTestId('mode-tab-think')
    const reasonTab = screen.getByTestId('mode-tab-reason')
    const createTab = screen.getByTestId('mode-tab-create')

    expect(thinkTab).toHaveClass('active')

    // Click Reason
    fireEvent.click(reasonTab)
    expect(reasonTab).toHaveClass('active')
    expect(thinkTab).not.toHaveClass('active')

    // Click Create
    fireEvent.click(createTab)
    expect(createTab).toHaveClass('active')
    expect(reasonTab).not.toHaveClass('active')
  })

  // 8. Bottom-Right Corner Floating Action Button & Speed-Dial Chart of Buttons
  it('Bottom-Right floating trigger opens speed-dial chart with all subsystem buttons and closes smoothly', () => {
    const onSelectPrompt = vi.fn()
    const onOpenPlugins = vi.fn()
    const onOpenKnowledge = vi.fn()
    const onOpenWorkspaces = vi.fn()

    render(
      <RightSidebar
        transportType="mock"
        connectionState="connected"
        onSelectPrompt={onSelectPrompt}
        onOpenPlugins={onOpenPlugins}
        onOpenKnowledge={onOpenKnowledge}
        onOpenWorkspaces={onOpenWorkspaces}
      />
    )

    // 1. Floating trigger button exists at bottom-right corner
    const triggerBtn = screen.getByTestId('floating-hub-trigger')
    expect(triggerBtn).toBeInTheDocument()
    expect(screen.getByText('Quick Actions')).toBeInTheDocument()

    // Panel is initially closed
    const panel = screen.getByTestId('right-sidebar')
    expect(panel).not.toHaveClass('open')

    // 2. Click trigger button to expand chart
    fireEvent.click(triggerBtn)
    expect(panel).toHaveClass('open')

    // 3. Subsystem direct jumper buttons exist and dispatch events
    const freelanceChip = screen.getByText(/💼 Freelance/i)
    fireEvent.click(freelanceChip)
    expect(onOpenWorkspaces).toHaveBeenCalledWith('freelance')
    // After clicking subsystem chip, panel closes
    expect(panel).not.toHaveClass('open')

    // Open again and click quick prompt
    fireEvent.click(triggerBtn)
    expect(panel).toHaveClass('open')
    const quickSiteBtn = screen.getByTestId('quick-action-create-site')
    fireEvent.click(quickSiteBtn)
    expect(onSelectPrompt).toHaveBeenCalledWith('Create a modern, responsive website with interactive components')
    expect(panel).not.toHaveClass('open')

    // 4. Test keyboard Escape closes panel
    fireEvent.click(triggerBtn)
    expect(panel).toHaveClass('open')
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(panel).not.toHaveClass('open')
  })
})

