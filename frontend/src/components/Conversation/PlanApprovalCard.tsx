import React, { useState } from 'react'
import type { StagedPlanData, StagedPlanStep } from '../../types/conversation'
import './PlanApprovalCard.css'

export interface PlanApprovalCardProps {
  plan?: StagedPlanData | Record<string, any> | null
  isExecuting?: boolean
  onProceed?: (planText?: string) => void
  onRevise?: (planId?: string) => void
  onCancel?: (planId?: string) => void
}

export const PlanApprovalCard: React.FC<PlanApprovalCardProps> = ({
  plan,
  isExecuting: externalExecuting = false,
  onProceed,
  onRevise,
  onCancel,
}) => {
  const [internalExecuting, setInternalExecuting] = useState(false)
  const isExecuting = externalExecuting || internalExecuting

  if (!plan) return null

  const goal = plan.goal || 'Autonomous Task Execution Plan'
  const rawSteps: (StagedPlanStep | string)[] = plan.steps || []
  const steps: StagedPlanStep[] = rawSteps.map((s, idx) => {
    if (typeof s === 'string') {
      return { id: idx + 1, description: s, status: 'pending' }
    }
    return {
      id: s.id ?? idx + 1,
      description: s.description || `Step ${idx + 1}`,
      status: s.status || 'pending',
      action_type: s.action_type,
      tool: s.tool,
    }
  })

  const riskLevel = (plan.risk_level || 'standard').toLowerCase()

  const handleProceed = () => {
    if (isExecuting) return
    setInternalExecuting(true)
    onProceed?.('proceed to the plan')
  }

  return (
    <div
      className="plan-approval-card"
      data-testid="plan-approval-card"
      role="region"
      aria-label={`Task Plan: ${goal}`}
    >
      <div className="plan-card-ambient-glow" />

      {/* Header telemetry ribbon */}
      <div className="plan-card-header">
        <div className="plan-header-badge">
          <span className="plan-radar-dot" />
          <span className="plan-header-title">Plan Staged // Safety Gated</span>
        </div>

        <span
          className={`plan-risk-tag ${riskLevel}`}
          data-testid="plan-risk-tag"
          title={`Safety classification: ${riskLevel}`}
        >
          {riskLevel} risk
        </span>
      </div>

      {/* Objective block */}
      <div className="plan-goal-block">
        <span className="plan-goal-label">Target Objective</span>
        <h4 className="plan-goal-text">{goal}</h4>
      </div>

      {/* Sequenced steps */}
      {steps.length > 0 && (
        <div className="plan-steps-list" role="list">
          {steps.map((step, idx) => {
            const numStr = String(idx + 1).padStart(2, '0')
            const isDone = step.status === 'completed'
            const isStepActive = isExecuting && idx === 0 && !isDone
            return (
              <div
                key={step.id || idx}
                className="plan-step-item"
                data-testid="plan-step-item"
                role="listitem"
              >
                <span className="plan-step-num">{numStr}</span>
                <div className="plan-step-content">
                  <div className="plan-step-desc">{step.description}</div>
                  {(step.action_type || step.tool) && (
                    <div className="plan-step-meta">
                      <span className="plan-step-tool-badge">
                        {step.tool || step.action_type}
                      </span>
                    </div>
                  )}
                </div>
                <div className="plan-step-status-icon">
                  {isDone ? (
                    '✅'
                  ) : isStepActive ? (
                    <span className="plan-spinner" />
                  ) : (
                    '⏳'
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Safety Gating Notice */}
      <div className="plan-safety-notice">
        <span className="plan-safety-icon">🛡️</span>
        <span>
          Strict plan-first gating: Xeren holds all write actions until you authorize execution.
        </span>
      </div>

      {/* Action Buttons */}
      <div className="plan-actions-group">
        {isExecuting ? (
          <div className="plan-executing-indicator" data-testid="plan-executing-indicator">
            <span className="plan-spinner" />
            <span>Executing Autonomous Plan...</span>
          </div>
        ) : (
          <>
            <button
              type="button"
              className="plan-proceed-btn"
              onClick={handleProceed}
              data-testid="plan-proceed-btn"
            >
              <span className="plan-proceed-icon">⚡</span>
              <span>Proceed to the Plan</span>
            </button>

            {onRevise && (
              <button
                type="button"
                className="plan-revise-btn"
                onClick={() => onRevise(plan.plan_id)}
                data-testid="plan-revise-btn"
              >
                <span>✏️</span>
                <span>Revise Plan</span>
              </button>
            )}

            {onCancel && (
              <button
                type="button"
                className="plan-cancel-btn"
                onClick={() => onCancel(plan.plan_id)}
                data-testid="plan-cancel-btn"
              >
                Cancel
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default PlanApprovalCard
