import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ConnectedAppsModal } from '../components/ConnectedAppsModal/ConnectedAppsModal'

describe('Connected Apps: User Account Login & App Activity Logs', () => {
  const originalFetch = window.fetch

  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
    window.fetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/api/accounts/logs')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ logs: [] }),
        } as unknown as Response)
      }
      if (typeof url === 'string' && url.includes('/api/accounts/login')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, message: 'Logged in successfully' }),
        } as unknown as Response)
      }
      if (typeof url === 'string' && url.includes('/api/accounts')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ accounts: [] }),
        } as unknown as Response)
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ servers: [] }),
      } as unknown as Response)
    })
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    window.fetch = originalFetch
  })

  it('renders User Accounts tab by default with pre-configured platforms (Gemini, Canva, Hugging Face, etc.) and SVG logos', () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} initialTab="accounts" />)

    expect(screen.getByTestId('tab-user-accounts')).toHaveClass('active')
    expect(screen.getByTestId('user-accounts-tab-content')).toBeInTheDocument()

    // Core and expanded user accounts visible across categories
    expect(screen.getByText('Google Gemini')).toBeInTheDocument()
    expect(screen.getByText('Canva Design')).toBeInTheDocument()
    expect(screen.getByText('Hugging Face')).toBeInTheDocument()
    expect(screen.getByText('OpenAI / ChatGPT')).toBeInTheDocument()
    expect(screen.getByText('Anthropic Claude')).toBeInTheDocument()
    expect(screen.getByText('Perplexity AI')).toBeInTheDocument()
    expect(screen.getByText('Midjourney AI')).toBeInTheDocument()
    expect(screen.getByText('GitHub Account')).toBeInTheDocument()
    expect(screen.getByText('Supabase Cloud')).toBeInTheDocument()
    expect(screen.getByText('Notion Workspace')).toBeInTheDocument()
    expect(screen.getByText('Google Drive & Workspace')).toBeInTheDocument()
    expect(screen.getByText('Slack Workspace')).toBeInTheDocument()
    expect(screen.getByText('Discord Community')).toBeInTheDocument()
    expect(screen.getByText('Spotify Audio & Media')).toBeInTheDocument()
    expect(screen.getByText('Linear Issue Tracking')).toBeInTheDocument()
    expect(screen.getByText('Figma Studio')).toBeInTheDocument()

    // Official brand SVG logos rendered
    expect(screen.getByLabelText('Google Gemini logo')).toBeInTheDocument()
    expect(screen.getByLabelText('Canva logo')).toBeInTheDocument()
    expect(screen.getByLabelText('OpenAI logo')).toBeInTheDocument()
    expect(screen.getByLabelText('Discord logo')).toBeInTheDocument()
    expect(screen.getByLabelText('Spotify logo')).toBeInTheDocument()
    expect(screen.getByLabelText('Supabase logo')).toBeInTheDocument()

    // Security banner present
    expect(screen.getByText(/AES-256-GCM Hardware Encrypted/i)).toBeInTheDocument()
  })

  it('allows logging in to Google Gemini with user email, token, and tier, updating status to Logged In', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} initialTab="accounts" />)

    // Open Gemini login modal
    const geminiLoginBtn = screen.getByTestId('login-btn-gemini')
    fireEvent.click(geminiLoginBtn)

    expect(screen.getByTestId('login-modal-card')).toBeInTheDocument()
    expect(screen.getByText('Log In to Google Gemini')).toBeInTheDocument()

    // Fill in credentials
    const emailInput = screen.getByTestId('login-input-email')
    const tokenInput = screen.getByTestId('login-input-token')
    const submitBtn = screen.getByTestId('submit-account-login-btn')

    fireEvent.change(emailInput, { target: { value: 'leela@developer.ai' } })
    fireEvent.change(tokenInput, { target: { value: 'AIzaSyA_SecretKey998877' } })

    // Submit form
    await act(async () => {
      fireEvent.click(submitBtn)
    })

    // Advance timers for feedback dialog dismiss
    act(() => {
      vi.advanceTimersByTime(1100)
    })

    // Gemini card should now be authenticated
    const geminiCard = screen.getByTestId('account-card-gemini')
    expect(geminiCard).toHaveClass('authenticated')
    expect(geminiCard).toHaveTextContent('✓ Logged In')
    expect(geminiCard).toHaveTextContent('leela@developer.ai')
    expect(geminiCard).toHaveTextContent('AIz•••••••8877') // Masked token verification
    expect(geminiCard).toHaveTextContent('PRO')
    expect(screen.getByTestId('switch-account-gemini')).toBeInTheDocument()
    expect(screen.getByTestId('logout-account-gemini')).toBeInTheDocument()
  })

  it('records authentication in App Log tab, enables search, filtering, and clearing logs', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} initialTab="accounts" />)

    // 1. Log in to Canva
    const canvaLoginBtn = screen.getByTestId('login-btn-canva')
    fireEvent.click(canvaLoginBtn)

    fireEvent.change(screen.getByTestId('login-input-email'), { target: { value: 'creative@studio.design' } })
    fireEvent.change(screen.getByTestId('login-input-token'), { target: { value: 'canva_connect_token_45678' } })

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-account-login-btn'))
    })

    act(() => {
      vi.advanceTimersByTime(1100)
    })

    // 2. Switch to App Log tab
    const logsTabBtn = screen.getByTestId('tab-app-logs')
    fireEvent.click(logsTabBtn)

    expect(screen.getByTestId('app-logs-tab-content')).toBeInTheDocument()
    expect(screen.getByText('App Activity & Session Log')).toBeInTheDocument()

    // 3. Verify Canva AUTH entry exists
    const logsList = screen.getByTestId('log-entries-list')
    expect(logsList).toHaveTextContent('creative@studio.design')
    expect(logsList).toHaveTextContent(/Logged in as user account 'creative@studio.design'/i)

    // 4. Test Search Filter
    const searchInput = screen.getByTestId('logs-search-input')
    fireEvent.change(searchInput, { target: { value: 'creative@studio' } })
    expect(logsList).toHaveTextContent('creative@studio.design')

    fireEvent.change(searchInput, { target: { value: 'non_existent_search_query_xyz' } })
    expect(screen.getByText('No activity logs matched your current filters.')).toBeInTheDocument()

    // Reset search
    fireEvent.change(searchInput, { target: { value: '' } })

    // 5. Test App Filter
    const appFilter = screen.getByTestId('filter-app-select')
    fireEvent.change(appFilter, { target: { value: 'canva' } })
    expect(logsList).toHaveTextContent('creative@studio.design')

    // 6. Test Clear Log
    const clearBtn = screen.getByTestId('clear-logs-btn')
    await act(async () => {
      fireEvent.click(clearBtn)
    })
    expect(screen.getByText('No activity logs matched your current filters.')).toBeInTheDocument()
  })

  it('allows user to log out an account and revokes active session', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} initialTab="accounts" />)

    // Log in to Hugging Face
    fireEvent.click(screen.getByTestId('login-btn-huggingface'))
    fireEvent.change(screen.getByTestId('login-input-email'), { target: { value: 'hf_researcher@lab.org' } })
    fireEvent.change(screen.getByTestId('login-input-token'), { target: { value: 'hf_token_secret_12345678' } })

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-account-login-btn'))
    })

    act(() => {
      vi.advanceTimersByTime(1100)
    })

    const hfCard = screen.getByTestId('account-card-huggingface')
    expect(hfCard).toHaveClass('authenticated')

    // Log out
    const logoutBtn = screen.getByTestId('logout-account-huggingface')
    await act(async () => {
      fireEvent.click(logoutBtn)
    })

    expect(hfCard).not.toHaveClass('authenticated')
    expect(hfCard).toHaveTextContent('Not Connected')
    expect(screen.getByTestId('login-btn-huggingface')).toBeInTheDocument()
  })

  it('renders Blender 3D and native local device apps with official logos and links without an API key', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} initialTab="accounts" />)

    // 1. Verify Blender 3D and local device apps are present
    expect(screen.getByTestId('account-card-blender')).toBeInTheDocument()
    expect(screen.getByText('Visual Studio Code')).toBeInTheDocument()
    expect(screen.getByText('OBS Studio')).toBeInTheDocument()
    expect(screen.getByText('VLC Media Player')).toBeInTheDocument()
    expect(screen.getByText('GIMP Image Editor')).toBeInTheDocument()

    // 2. Verify official SVG logos
    expect(screen.getByLabelText('Blender logo')).toBeInTheDocument()
    expect(screen.getByLabelText('Visual Studio Code logo')).toBeInTheDocument()
    expect(screen.getByLabelText('OBS Studio logo')).toBeInTheDocument()
    expect(screen.getByLabelText('VLC logo')).toBeInTheDocument()
    expect(screen.getByLabelText('GIMP logo')).toBeInTheDocument()

    // 3. Test filtering by local device apps
    const localFilterBtn = screen.getByTestId('filter-local-apps')
    fireEvent.click(localFilterBtn)
    expect(screen.getByTestId('account-card-blender')).toBeInTheDocument()
    expect(screen.queryByTestId('account-card-gemini')).not.toBeInTheDocument()

    // 4. Link Blender 3D without entering an API key
    const blenderLinkBtn = screen.getByTestId('login-btn-blender')
    expect(blenderLinkBtn).toHaveTextContent('⚡ Link to Device (No API Key)')
    fireEvent.click(blenderLinkBtn)

    expect(screen.getByText('Link Blender 3D on Device')).toBeInTheDocument()
    const modal = screen.getByTestId('login-modal-card')
    expect(modal).toHaveTextContent('No API Key Required')

    // Submit without providing an API key
    const submitBtn = screen.getByTestId('submit-account-login-btn')
    expect(submitBtn).toHaveTextContent('⚡ Link Application to Device')

    await act(async () => {
      fireEvent.click(submitBtn)
    })

    act(() => {
      vi.advanceTimersByTime(1100)
    })

    // Blender should now be linked
    const blenderCard = screen.getByTestId('account-card-blender')
    expect(blenderCard).toHaveClass('authenticated')
    expect(blenderCard).toHaveTextContent('✓ Linked')
    expect(blenderCard).toHaveTextContent('LOCAL DEVICE')
    expect(blenderCard).toHaveTextContent('local:blender')
  })

  it('allows registering a custom local device application from user PC without an API key', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} initialTab="accounts" />)

    // Open "Add Application" modal
    const addAppBtn = screen.getByTestId('add-local-app-btn')
    fireEvent.click(addAppBtn)

    expect(screen.getByTestId('add-local-device-modal')).toBeInTheDocument()
    expect(screen.getByText('Add Application or Custom Service')).toBeInTheDocument()

    // Switch to local device mode
    const localDeviceBtn = screen.getByText('🖥️ Local Device App')
    fireEvent.click(localDeviceBtn)

    // Fill in custom app details
    const nameInput = screen.getByTestId('custom-app-name-input')
    const pathInput = screen.getByTestId('custom-app-path-input')
    const submitBtn = screen.getByTestId('submit-add-local-app-btn')

    fireEvent.change(nameInput, { target: { value: 'Godot Engine' } })
    fireEvent.change(pathInput, { target: { value: 'godot.exe' } })

    await act(async () => {
      fireEvent.click(submitBtn)
    })

    // Custom app should now be listed in the accounts grid
    expect(screen.getByText('Godot Engine')).toBeInTheDocument()
    const godotCard = screen.getByTestId('account-card-godot-engine')
    expect(godotCard).toBeInTheDocument()
    expect(godotCard).toHaveTextContent('✓ Linked')
  })

  it('allows adding a custom web application with URL endpoint, API key, and user details', async () => {
    render(<ConnectedAppsModal isOpen={true} onClose={vi.fn()} initialTab="accounts" />)

    // Open "Add Application" modal
    const addAppBtn = screen.getByTestId('add-local-app-btn')
    fireEvent.click(addAppBtn)

    expect(screen.getByTestId('add-local-device-modal')).toBeInTheDocument()

    // Fill in URL part, API key part, and user details part
    const nameInput = screen.getByTestId('custom-app-name-input')
    const urlInput = screen.getByTestId('custom-app-url-input')
    const keyInput = screen.getByTestId('custom-app-key-input')
    const emailInput = screen.getByTestId('custom-app-email-input')
    const usernameInput = screen.getByTestId('custom-app-username-input')
    const submitBtn = screen.getByTestId('submit-add-local-app-btn')

    fireEvent.change(nameInput, { target: { value: 'Ollama Private Gateway' } })
    fireEvent.change(urlInput, { target: { value: 'http://localhost:11434/v1' } })
    fireEvent.change(keyInput, { target: { value: 'sk-test-secret-gateway-12345' } })
    fireEvent.change(emailInput, { target: { value: 'researcher@ai.lab' } })
    fireEvent.change(usernameInput, { target: { value: 'Leela AI' } })

    await act(async () => {
      fireEvent.click(submitBtn)
    })

    // Custom app should now be in the catalog with URL, user details, and masked key
    expect(screen.getByText('Ollama Private Gateway')).toBeInTheDocument()
    const ollamaCard = screen.getByTestId('account-card-ollama-private-gateway')
    expect(ollamaCard).toBeInTheDocument()
    expect(ollamaCard).toHaveTextContent('http://localhost:11434/v1')
    expect(ollamaCard).toHaveTextContent('researcher@ai.lab')
    expect(ollamaCard).toHaveTextContent('sk-•••••••2345')
    expect(ollamaCard).toHaveTextContent('✓ Logged In')
    expect(ollamaCard).toHaveTextContent('🌐 CUSTOM API')
  })
})


