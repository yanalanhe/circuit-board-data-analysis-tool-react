'use client'

import React from 'react'

interface PlanPanelProps {
  plan: string[] | null
  intent: 'report' | 'qa' | 'chat'
  isExecuting: boolean
  onExecute: () => void
  onSaveTemplate?: (name: string) => void
  canSaveTemplate?: boolean
  isSaving?: boolean
}

/**
 * PlanPanel Component - Displays execution plan and Execute button
 *
 * Renders the generated execution plan as a numbered list of steps.
 * Shows an Execute button to trigger code generation and execution.
 * Only visible when intent is 'report' and a plan is available.
 *
 * AC #1: Plan displays as numbered list of steps
 * AC #2: Execute button is prominently displayed
 * AC #5: Plan is preserved when switching tabs (parent manages state)
 * AC #6: No plan/button shown when intent != 'report'
 */
export function PlanPanel({
  plan,
  intent,
  isExecuting,
  onExecute,
  onSaveTemplate,
  canSaveTemplate = false,
  isSaving = false,
}: PlanPanelProps) {
  // Only show plan if intent is 'report' and plan exists (AC #6)
  if (intent !== 'report' || !plan) {
    return null
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Plan List Section */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          {plan.map((step, index) => (
            <div key={index} className="flex gap-3 text-sm">
              {/* Step Number */}
              <span className="text-blue-600 dark:text-blue-400 font-semibold flex-shrink-0">
                {index + 1}.
              </span>
              {/* Step Text */}
              <span className="text-gray-700 dark:text-gray-300 leading-relaxed text-sm">
                {step}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Execute Button Section */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800">
        <button
          onClick={onExecute}
          disabled={isExecuting}
          className={`w-full py-2 px-4 rounded-md font-medium text-white transition-colors ${
            isExecuting
              ? 'bg-gray-400 cursor-not-allowed opacity-60'
              : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
          }`}
        >
          {isExecuting ? 'Executing...' : 'Execute Analysis'}
        </button>
        {canSaveTemplate && (
          <button
            onClick={() => {
              const name = window.prompt('Enter a name for this template:')
              if (name && name.trim()) {
                onSaveTemplate?.(name.trim())
              }
            }}
            disabled={isSaving}
            className="w-full mt-2 py-2 px-4 rounded-md font-medium text-blue-600 dark:text-blue-400 border border-blue-600 dark:border-blue-400 bg-white dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? 'Saving…' : 'Save as Template'}
          </button>
        )}
      </div>
    </div>
  )
}
