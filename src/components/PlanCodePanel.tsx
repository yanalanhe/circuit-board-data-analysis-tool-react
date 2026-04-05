'use client'

import React from 'react'
import { TemplateItem } from '@/types/api'
import { PlanPanel } from './PlanPanel'
import CodeViewerPanel from './CodeViewerPanel'

interface PlanCodePanelProps {
  activeTab: 'plan' | 'code' | 'template'
  onTabChange: (tab: 'plan' | 'code' | 'template') => void
  plan: string[] | null
  intent: 'report' | 'qa' | 'chat'
  isExecuting: boolean
  onExecute: () => void
  code: string | null
  onRerun?: (code: string) => void
  isRerunning?: boolean
  codeError?: string | null
  onSaveTemplate?: (name: string) => void
  canSaveTemplate?: boolean
  isSaving?: boolean
  savedTemplateCount?: number
  savedTemplates?: TemplateItem[]
  onApplyTemplate?: (template: TemplateItem) => void
}

export default function PlanCodePanel({
  activeTab,
  onTabChange,
  plan,
  intent,
  isExecuting,
  onExecute,
  code,
  onRerun,
  isRerunning,
  codeError,
  onSaveTemplate,
  canSaveTemplate,
  isSaving,
  savedTemplateCount: _savedTemplateCount = 0,
  savedTemplates = [],
  onApplyTemplate,
}: PlanCodePanelProps) {
  const tabs: Array<'plan' | 'code' | 'template'> = [
    'plan',
    'code',
    'template',
  ]

  const getTabLabel = (tab: 'plan' | 'code' | 'template') => {
    return tab.charAt(0).toUpperCase() + tab.slice(1)
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      {/* Header with Tabs */}
      <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
        {/* Tab Title */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="font-bold text-sm text-gray-900 dark:text-gray-100">
            Plan / Code / Template
          </h2>
        </div>

        {/* Tab Buttons */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100 border-b-2 border-blue-500'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {getTabLabel(tab)}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Plan Tab */}
        {activeTab === 'plan' && (
          <PlanPanel
            plan={plan}
            intent={intent}
            isExecuting={isExecuting}
            onExecute={onExecute}
            onSaveTemplate={onSaveTemplate}
            canSaveTemplate={canSaveTemplate}
            isSaving={isSaving}
          />
        )}

        {/* Code Tab */}
        {activeTab === 'code' && (
          <div className="flex-1 overflow-hidden flex flex-col">
            <CodeViewerPanel
              code={code}
              onRerun={onRerun}
              isRerunning={isRerunning}
              codeError={codeError}
            />
          </div>
        )}

        {/* Template Tab */}
        {activeTab === 'template' && (
          <div className="flex-1 overflow-y-auto p-4">
            {savedTemplates.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-400 dark:text-gray-500 text-sm text-center italic">
                  No templates saved yet.<br />
                  Save a successful analysis using the &quot;Save as Template&quot; button in the Plan tab.
                </p>
              </div>
            ) : (
              <ul className="space-y-3">
                {savedTemplates.map((template, idx) => (
                  <li
                    key={idx}
                    className="border border-gray-200 dark:border-gray-700 rounded-md p-3 hover:border-blue-300 dark:hover:border-blue-600 cursor-pointer transition-colors"
                    onDoubleClick={() => onApplyTemplate?.(template)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
                          {template.name}
                        </p>
                        <p className="text-xs text-gray-500 mt-1 truncate">
                          {template.plan[0]
                            ? template.plan[0].slice(0, 80) + (template.plan[0].length > 80 ? '\u2026' : '')
                            : template.code.slice(0, 80) + (template.code.length > 80 ? '\u2026' : '')}
                        </p>
                      </div>
                      <button
                        onClick={() => onApplyTemplate?.(template)}
                        className="flex-shrink-0 px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700 transition-colors"
                      >
                        Apply
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
