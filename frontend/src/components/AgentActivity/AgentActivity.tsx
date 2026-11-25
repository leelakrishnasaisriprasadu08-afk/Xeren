import React, { useState } from 'react'
import type { AgentMilestone, AgentProgressDetails } from '../../types/agent'
import './AgentActivity.css'

interface AgentActivityProps {
  progressDetails: AgentProgressDetails | null
  activeMilestone: AgentMilestone | null
}

const MILESTONE_ORDER: AgentMilestone[] = [
  'understanding',
  'planning',
  'researching',
  'creating',
  'verifying',
  'completed',
]

export const AgentActivity: React.FC<AgentActivityProps> = ({
  progressDetails,
  activeMilestone,
}) => {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!progressDetails && !activeMilestone) {
    return null
  }

  const currentMilestone = activeMilestone || progressDetails?.milestone || 'understanding'
  const currentIndex = MILESTONE_ORDER.indexOf(currentMilestone)
  const percent = progressDetails?.progress_percent ?? Math.round(((currentIndex + 1) / MILESTONE_ORDER.length) * 100)

  return (
    <div className="agent-activity-bar" data-testid="agent-activity-bar">
      {/* High-level status pill */}
      <button
        type="button"
        className="milestone-pill"
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
        aria-label={`Task milestone: ${currentMilestone}, ${percent}% complete`}
        data-testid="milestone-pill"
      >
        <span className="milestone-dot" />
        <span className="milestone-text">{currentMilestone}</span>
        {progressDetails?.goal && (
          <span className="milestone-goal">— {progressDetails.goal}</span>
        )}
        <span className={`milestone-chevron ${isExpanded ? 'expanded' : ''}`}>▼</span>
      </button>

      {/* Expandable Activity Details (Non-cluttered) */}
      {isExpanded && (
        <div className="activity-drawer" data-testid="activity-drawer">
          <div className="drawer-header">
            <span className="drawer-title">Autonomous Action</span>
            <span className="drawer-phase">{progressDetails?.phase || currentMilestone}</span>
          </div>

          {progressDetails?.goal && (
            <div className="drawer-goal">
              <strong>Objective:</strong> {progressDetails.goal}
            </div>
          )}

          {/* 6 High-Level Milestones Stepper */}
          <div className="milestones-stepper">
            {MILESTONE_ORDER.map((step, idx) => {
              const isCompleted = idx < currentIndex
              const isActive = idx === currentIndex
              return (
                <div
                  key={step}
                  className={`step-node ${isCompleted ? 'completed' : ''} ${
                    isActive ? 'active' : ''
                  }`}
                  title={step.charAt(0).toUpperCase() + step.slice(1)}
                  data-testid={`step-node-${step}`}
                />
              )
            })}
          </div>

          {/* Progress bar */}
          <div className="progress-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
