import { describe, it, expect, vi } from 'vitest'
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MessageComposer } from '../components/MessageComposer/MessageComposer'
import { Conversation } from '../components/Conversation/Conversation'
import type { Message } from '../types/conversation'

describe('Multimodal Attachments & Image Paste Verification', () => {
  it('accepts clipboard paste of images (Ctrl+V) and renders image thumbnail in composer', async () => {
    const onSendMessage = vi.fn()

    render(
      <MessageComposer
        presenceState="idle"
        isListening={false}
        isSpeaking={false}
        isOnline={true}
        onSendMessage={onSendMessage}
        onStartListening={vi.fn()}
        onStopListening={vi.fn()}
        onInterrupt={vi.fn()}
      />
    )

    // Check online placeholder
    const input = screen.getByTestId('text-composer-input') as HTMLInputElement
    expect(input.placeholder).toContain('attach or paste images/files')

    // Simulate pasting an image File from clipboard
    const imageBlob = new Blob(['mock-png-binary-data'], { type: 'image/png' })
    const imageFile = new File([imageBlob], 'screenshot.png', { type: 'image/png' })

    const clipboardEvent = {
      preventDefault: vi.fn(),
      clipboardData: {
        items: [
          {
            type: 'image/png',
            kind: 'file',
            getAsFile: () => imageFile,
          },
        ],
      },
    }

    fireEvent.paste(input, clipboardEvent)

    // Tray appears and shows attachment chip
    expect(screen.getByTestId('attachments-tray')).toBeInTheDocument()
    const chip = screen.getByTestId('attachment-chip-screenshot.png')
    expect(chip).toBeInTheDocument()
    expect(chip).toHaveClass('is-image')

    // Type instructions and send
    fireEvent.change(input, { target: { value: 'Analyze this UI diagram' } })
    fireEvent.click(screen.getByTestId('send-message-button'))

    expect(onSendMessage).toHaveBeenCalledTimes(1)
    expect(onSendMessage).toHaveBeenCalledWith(
      expect.stringContaining('screenshot.png'),
      expect.arrayContaining([
        expect.objectContaining({
          name: 'screenshot.png',
          isImage: true,
        }),
      ])
    )
  })

  it('accepts drag-and-drop of image and file into composer dropzone', async () => {
    const onSendMessage = vi.fn()

    render(
      <MessageComposer
        presenceState="idle"
        isListening={false}
        isSpeaking={false}
        isOnline={true}
        onSendMessage={onSendMessage}
        onStartListening={vi.fn()}
        onStopListening={vi.fn()}
        onInterrupt={vi.fn()}
      />
    )

    const form = screen.getByTestId('text-composer-form')

    // Drag over activates dropzone overlay
    fireEvent.dragOver(form, { preventDefault: vi.fn(), stopPropagation: vi.fn() })
    expect(screen.getByTestId('drag-drop-overlay')).toBeInTheDocument()
    expect(form).toHaveClass('drag-over')

    // Drop files
    const droppedFile = new File(['{"api": "xeren"}'], 'config.json', { type: 'application/json' })
    fireEvent.drop(form, {
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
      dataTransfer: {
        files: [droppedFile],
      },
    })

    // Drag overlay disappears and attachment appears in tray
    expect(screen.queryByTestId('drag-drop-overlay')).not.toBeInTheDocument()
    expect(screen.getByTestId('attachment-chip-config.json')).toBeInTheDocument()
  })

  it('renders attached images in Conversation bubble and opens lightbox modal on click', async () => {
    const mockDataUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='

    const messages: Message[] = [
      {
        id: 'msg-user-1',
        role: 'user',
        content: 'Check this diagram',
        timestamp: Date.now(),
        attachments: [
          {
            id: 'att-1',
            name: 'diagram.png',
            size: 1024,
            type: 'image/png',
            isImage: true,
            dataUrl: mockDataUrl,
            tier: 'Liberal',
          },
          {
            id: 'att-2',
            name: 'specs.pdf',
            size: 2048,
            type: 'application/pdf',
            isImage: false,
            tier: 'Sensitive',
          },
        ],
      },
    ]

    render(<Conversation messages={messages} />)

    // User message row is present
    expect(screen.getByTestId('message-row-user')).toBeInTheDocument()

    // Attachments preview renders
    expect(screen.getByTestId('message-attachments-preview')).toBeInTheDocument()
    expect(screen.getByText('specs.pdf')).toBeInTheDocument()

    // Image card renders with alt text
    const imgElement = screen.getByAltText('diagram.png')
    expect(imgElement).toBeInTheDocument()
    expect(imgElement).toHaveAttribute('src', mockDataUrl)

    // Click image card to open lightbox
    const imgCard = imgElement.closest('.message-attachment-image-card')!
    fireEvent.click(imgCard)

    // Lightbox modal is displayed
    const lightbox = screen.getByTestId('attachment-lightbox')
    expect(lightbox).toBeInTheDocument()

    // Clicking close button dismisses lightbox
    const closeBtn = screen.getByLabelText('Close image preview')
    fireEvent.click(closeBtn)
    expect(screen.queryByTestId('attachment-lightbox')).not.toBeInTheDocument()
  })
})
