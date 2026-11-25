import React from 'react'
import './SuggestionChips.css'

interface SuggestionChipsProps {
  onSelectSuggestion: (text: string) => void
}

export const SuggestionChips: React.FC<SuggestionChipsProps> = ({ onSelectSuggestion }) => {
  const suggestions = [
    'Build a website for my startup',
    'Analyze the latest AI trends',
    'Find study resources',
    'Automate my workflow',
  ]

  return (
    <div
      className="suggestion-chips-container"
      role="group"
      aria-label="Prompt suggestions"
      data-testid="suggestion-chips-container"
    >
      {suggestions.map((text) => (
        <button
          key={text}
          type="button"
          className="suggestion-chip"
          onClick={() => onSelectSuggestion(text)}
          data-testid={`suggestion-chip-${text.toLowerCase().replace(/\s+/g, '-')}`}
        >
          <span className="chip-sparkle" aria-hidden="true">✦</span>
          <span>{text}</span>
        </button>
      ))}
    </div>
  )
}
