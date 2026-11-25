import React from 'react'
import './CapabilityCards.css'

interface CapabilityCardItem {
  id: string
  title: string
  description: string
  prompt: string
  icon: React.ReactNode
}

interface CapabilityCardsProps {
  onSelectPrompt: (prompt: string) => void
}

export const CapabilityCards: React.FC<CapabilityCardsProps> = ({ onSelectPrompt }) => {
  const cards: CapabilityCardItem[] = [
    {
      id: 'research',
      title: 'Research',
      description: 'Find latest information',
      prompt: 'Research the latest developments in autonomous AI systems',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      ),
    },
    {
      id: 'create',
      title: 'Create',
      description: 'Build websites & apps',
      prompt: 'Create a modern web application for my project',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      ),
    },
    {
      id: 'automate',
      title: 'Automate',
      description: 'Use AI agents & plugins',
      prompt: 'Automate my workflow using plugins and autonomous agents',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <rect x="9" y="9" width="6" height="6" />
          <line x1="9" y1="1" x2="9" y2="4" />
          <line x1="15" y1="1" x2="15" y2="4" />
          <line x1="9" y1="20" x2="9" y2="23" />
          <line x1="15" y1="20" x2="15" y2="23" />
        </svg>
      ),
    },
    {
      id: 'solve',
      title: 'Solve',
      description: 'Get step-by-step help',
      prompt: 'Help me solve this technical challenge step-by-step',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9 18h6" />
          <path d="M10 22h4" />
          <path d="M12 2a7 7 0 0 0-7 7c0 2.5 1.5 4.5 3 6h8c1.5-1.5 3-3.5 3-6a7 7 0 0 0-7-7z" />
        </svg>
      ),
    },
  ]

  return (
    <div className="capability-cards-grid" role="region" aria-label="Quick Capabilities">
      {cards.map((card) => (
        <button
          key={card.id}
          type="button"
          className="capability-card"
          onClick={() => onSelectPrompt(card.prompt)}
          data-testid={`capability-card-${card.id}`}
        >
          <div className="capability-card-icon" aria-hidden="true">
            {card.icon}
          </div>
          <div className="capability-card-title">{card.title}</div>
          <div className="capability-card-desc">{card.description}</div>
        </button>
      ))}
    </div>
  )
}
