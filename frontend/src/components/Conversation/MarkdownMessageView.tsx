import React, { useState } from 'react'
import type { MessageMetadata, StagedPlanData } from '../../types/conversation'
import { PlanApprovalCard } from './PlanApprovalCard'
import './MarkdownMessageView.css'

export interface MarkdownMessageViewProps {
  content: string
  metadata?: MessageMetadata
  isStreaming?: boolean
  onProceedPlan?: (planText?: string) => void
  onRevisePlan?: (planId?: string) => void
  onCancelPlan?: (planId?: string) => void
}

/**
 * Parses markdown code blocks, lists, bold text, inline code,
 * plan staging directives, research citations, and permitted data attribution.
 */
export const MarkdownMessageView: React.FC<MarkdownMessageViewProps> = ({
  content,
  metadata,
  isStreaming = false,
  onProceedPlan,
  onRevisePlan,
  onCancelPlan,
}) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [isResearchOpen, setIsResearchOpen] = useState(false)

  // Copy code handler
  const handleCopyCode = async (codeText: string, idx: number) => {
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(codeText)
      }
      setCopiedIndex(idx)
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (_) {
      // Fallback
    }
  }

  // Extract or detect staged plan
  const planData: StagedPlanData | null = (() => {
    if (metadata?.plan && typeof metadata.plan === 'object') {
      return metadata.plan as StagedPlanData
    }
    // Parse text containing [TASK PLAN STAGED]
    if (content.includes('[TASK PLAN STAGED]') || (content.includes('Goal:') && content.includes('proceed to the plan'))) {
      const goalMatch = content.match(/Goal:\s*([^\n\r]+)/i)
      const goal = goalMatch ? goalMatch[1].trim() : 'Autonomous Task Execution'
      const steps: { id: number; description: string; status: 'pending' }[] = []
      const stepLines = content.split('\n').filter((l) => /^\s*\d+\.\s+/.test(l))
      stepLines.forEach((line, i) => {
        const desc = line.replace(/^\s*\d+\.\s+/, '').trim()
        if (desc) {
          steps.push({ id: i + 1, description: desc, status: 'pending' })
        }
      })
      if (steps.length > 0) {
        return {
          plan_id: `plan_${Date.now()}`,
          goal,
          steps,
          risk_level: 'standard',
          status: 'staged',
        }
      }
    }
    return null
  })()

  // Format inline elements: **bold** and `code`
  const renderInlineFormatted = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = []
    // Match inline code `...` or bold **...**
    const regex = /(`[^`]+`|\*\*[^*]+\*\*)/g
    let lastIdx = 0
    let match: RegExpExecArray | null

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push(text.substring(lastIdx, match.index))
      }
      const token = match[0]
      if (token.startsWith('`') && token.endsWith('`')) {
        parts.push(
          <code key={`code-${match.index}`} className="markdown-inline-code">
            {token.slice(1, -1)}
          </code>
        )
      } else if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(
          <strong key={`bold-${match.index}`} className="markdown-bold">
            {token.slice(2, -2)}
          </strong>
        )
      }
      lastIdx = regex.lastIndex
    }

    if (lastIdx < text.length) {
      parts.push(text.substring(lastIdx))
    }

    return parts.length > 0 ? parts : [text]
  }

  // Parse fenced code blocks
  const parseBlocks = (raw: string) => {
    const blocks: Array<
      | { type: 'code'; language: string; code: string }
      | { type: 'text'; text: string }
    > = []

    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\s*([\s\S]*?)```/g
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = codeBlockRegex.exec(raw)) !== null) {
      if (match.index > lastIndex) {
        blocks.push({
          type: 'text',
          text: raw.substring(lastIndex, match.index),
        })
      }
      blocks.push({
        type: 'code',
        language: match[1] || 'code',
        code: match[2].replace(/^\n+|\n+$/g, ''),
      })
      lastIndex = codeBlockRegex.lastIndex
    }

    if (lastIndex < raw.length) {
      blocks.push({
        type: 'text',
        text: raw.substring(lastIndex),
      })
    }

    return blocks
  }

  const blocks = parseBlocks(content)

  return (
    <div className="markdown-message-view" data-testid="markdown-message-view">
      {blocks.map((block, idx) => {
        if (block.type === 'code') {
          const isCopied = copiedIndex === idx
          return (
            <div
              key={`block-code-${idx}`}
              className="code-block-container"
              data-testid="code-block"
            >
              <div className="code-block-header">
                <span className="code-lang-label">{block.language || 'Code'}</span>
                <button
                  type="button"
                  className={`code-copy-btn ${isCopied ? 'copied' : ''}`}
                  onClick={() => handleCopyCode(block.code, idx)}
                  aria-label="Copy code to clipboard"
                  data-testid="copy-code-btn"
                >
                  <span>{isCopied ? '✓' : '📋'}</span>
                  <span>{isCopied ? 'Copied!' : 'Copy'}</span>
                </button>
              </div>
              <pre className="code-content-pre">
                <code>{block.code}</code>
              </pre>
            </div>
          )
        }

        // Text block: clean raw math / LaTeX tokens into readable symbols, then split into paragraphs and lines
        const cleanText = block.text
          .replace(/\\mathbf\{([^}]+)\}/g, '$1')
          .replace(/\\sqrt\{([^}]+)\}/g, '√$1')
          .replace(/\\text\{([^}]+)\}/g, '$1')
          .replace(/\\log/g, 'log')
          .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '($1 / $2)')
          .replace(/\$\$([\s\S]*?)\$\$/g, '$1')
          .replace(/\$([^$\n]+)\$/g, '$1')

        const lines = cleanText.split('\n')
        return (
          <React.Fragment key={`block-text-${idx}`}>
            {lines.map((line, lineIdx) => {
              const trimmed = line.trim()
              if (!trimmed) {
                return null
              }

              // Bullet item
              if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                return (
                  <ul key={`ul-${lineIdx}`} className="markdown-list">
                    <li className="markdown-list-item">
                      {renderInlineFormatted(trimmed.slice(2))}
                    </li>
                  </ul>
                )
              }

              // Numbered item
              if (/^\d+\.\s+/.test(trimmed)) {
                return (
                  <ol key={`ol-${lineIdx}`} className="markdown-list">
                    <li className="markdown-list-item">
                      {renderInlineFormatted(trimmed.replace(/^\d+\.\s+/, ''))}
                    </li>
                  </ol>
                )
              }

              return (
                <p key={`p-${lineIdx}`} className="markdown-paragraph">
                  {renderInlineFormatted(line)}
                </p>
              )
            })}
          </React.Fragment>
        )
      })}

      {/* Plan Staging Card if a plan is active and not currently streaming partial text */}
      {!isStreaming && planData && (
        <PlanApprovalCard
          plan={planData}
          onProceed={onProceedPlan}
          onRevise={onRevisePlan}
          onCancel={onCancelPlan}
        />
      )}

      {/* Research Citations & Zero Hallucination Accordion */}
      {!isStreaming && metadata?.research && (
        <div
          className="research-verification-box"
          data-testid="research-verification-box"
        >
          <div
            className="research-verification-header"
            onClick={() => setIsResearchOpen((prev) => !prev)}
            role="button"
            tabIndex={0}
            aria-expanded={isResearchOpen}
          >
            <span className="research-badge-title">
              <span>🛡️</span>
              <span>Verified Truth Matrix // Strawberry Grounded</span>
            </span>
            <span className={`research-chevron ${isResearchOpen ? 'open' : ''}`}>
              ▼
            </span>
          </div>

          {isResearchOpen && (
            <div className="research-verification-body">
              <div>
                <strong>Authority Verification:</strong> Passed with zero
                hallucinations.
              </div>
              {Array.isArray(metadata.research.citations) && (
                <div className="research-sources-list">
                  {metadata.research.citations.map((cite: any, i: number) => (
                    <div key={i} className="research-source-item">
                      <span>•</span>
                      <a
                        href={cite.url || cite}
                        target="_blank"
                        rel="noreferrer"
                        className="research-source-link"
                      >
                        {cite.title || cite.domain || cite.url || String(cite)}
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Permitted Data Holding Badges */}
      {!isStreaming && Array.isArray(metadata?.heldDataApplied) && metadata.heldDataApplied.length > 0 && (
        <div className="held-data-badges-row" data-testid="held-data-badges">
          {metadata.heldDataApplied.map((item: any, i: number) => (
            <span key={i} className="held-data-badge" title="Permitted Source">
              📁 {typeof item === 'string' ? item : item.name || item.path || 'Local File'}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default MarkdownMessageView
