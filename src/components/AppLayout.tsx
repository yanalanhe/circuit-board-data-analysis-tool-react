'use client'

import React, { useState, useCallback, useEffect } from 'react'
import { useApi } from '@/hooks/useApi'
import { ReportData, TemplateItem, TemplatesData } from '@/types/api'
import ChatPanel from './ChatPanel'
import PlanCodePanel from './PlanCodePanel'
import DataPanel from './DataPanel'
import ReportPanel from './ReportPanel'
import ThemeToggle from './ThemeToggle'

const USAGE_EXAMPLE = `1. Generate a scatter plot for columns A vs B.
2. Generate a scatter plot for columns A vs C.
3. Label the axes and the title of each scatter plot for clear understanding.
4. Plot python_mpl.tool_how, way to make scatter plot.
5. Observe the relationship between A and B.
6. Observe the relationship between A and C.
7. Draw conclusions about these relationships based on the scatter plots.
8. Present conclusions about the scatter plots.
9. Present conclusions about the relationships between columns A, B, and C.
10. Include the scatter plots in the report to support your conclusions.`

export default function AppLayout() {
  const [usageOpen, setUsageOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'plan' | 'code' | 'template'>(
    'plan'
  )
  const [plan, setPlan] = useState<string[] | null>(null)
  const [intent, setIntent] = useState<'report' | 'qa' | 'chat'>('chat')
  const [isExecuting, setIsExecuting] = useState(false)
  const [isRerunning, setIsRerunning] = useState(false)
  const [reportCharts, setReportCharts] = useState<string[]>([])
  const [reportText, setReportText] = useState<string | null>(null)
  const [currentCode, setCurrentCode] = useState<string | null>(null)
  const [codeError, setCodeError] = useState<string | null>(null)
  const [savedTemplates, setSavedTemplates] = useState<TemplateItem[]>([])
  const [isSavingTemplate, setIsSavingTemplate] = useState(false)
  const { executeAnalysis, apiCall, session_id } = useApi()

  // Load saved templates on app mount (AC #6 — GET /api/templates on init)
  useEffect(() => {
    apiCall<TemplatesData>('/api/templates', 'GET').then((response) => {
      if (response.status === 'success' && response.data) {
        setSavedTemplates(response.data.templates)
      }
    })
  }, [apiCall])

  // canSaveTemplate — true after a successful analysis produces code and charts
  const canSaveTemplate = currentCode !== null && reportCharts.length > 0

  // Handle execute button click (Task 3.2)
  const handleExecute = useCallback(async () => {
    if (!executeAnalysis) return

    setIsExecuting(true)
    try {
      // Call executeAnalysis — backend is synchronous, blocks until pipeline completes
      await executeAnalysis()

      // Pipeline done — fetch report results
      const response = await apiCall<ReportData>('/api/report', 'GET')
      if (response.status === 'success' && response.data) {
        setReportCharts(response.data.charts)
        setReportText(response.data.text || null)
        setCurrentCode(response.data.code || null)
      }
    } catch (error) {
      console.error('Execute failed:', error)
    } finally {
      setIsExecuting(false)
    }
  }, [executeAnalysis, apiCall])

  // Handle Save as Template from Plan tab (AC: Story 11.1)
  const handleSaveTemplate = useCallback(async (name: string) => {
    setIsSavingTemplate(true)
    try {
      const response = await apiCall('/api/templates', 'POST', {
        session_id,
        name,
        plan: plan ?? [],
        code: currentCode ?? '',
      })
      if (response.status === 'success') {
        setSavedTemplates((prev) => [
          ...prev,
          { name, plan: plan ?? [], code: currentCode ?? '' },
        ])
      }
    } catch (error) {
      console.error('Save template failed:', error)
    } finally {
      setIsSavingTemplate(false)
    }
  }, [apiCall, session_id, plan, currentCode])

  // Handle Apply Template from Template tab (AC: Story 11.2)
  // Zero API calls — all data already in client-side savedTemplates state (AC #3)
  const handleApplyTemplate = useCallback((template: TemplateItem) => {
    setPlan(template.plan)
    setCurrentCode(template.code)
    setIntent('report')   // templates always come from successful report analyses
    setActiveTab('plan')  // switch to plan tab so user sees the loaded plan immediately
  }, [])

  // Handle Re-run button click from Code tab (AC: Story 10.2)
  const handleRerun = useCallback(async (editedCode: string) => {
    setIsRerunning(true)
    setCodeError(null)
    try {
      const response = await apiCall<ReportData>('/api/code', 'PUT', {
        session_id,
        code: editedCode,
      })
      if (response.status === 'error') {
        if (response.error?.code === 'VALIDATION_ERROR') {
          // Show inline in Code tab — do NOT update report panel
          setCodeError(response.error.message)
        } else {
          // EXECUTION_ERROR or other — show translated message in Report panel
          setReportText(response.error?.message || 'Execution failed.')
          setCodeError(null)
        }
      } else if (response.status === 'success' && response.data) {
        setReportCharts(response.data.charts)
        setReportText(response.data.text || null)
        setCurrentCode(response.data.code)
        setCodeError(null)
      }
    } catch (error) {
      console.error('Re-run failed:', error)
    } finally {
      setIsRerunning(false)
    }
  }, [apiCall, session_id])

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900 overflow-hidden">
      <ThemeToggle />

      {/* Title Bar */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <span className="text-2xl">🔧</span>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Circuit Board Data Analysis Tool
        </h1>
      </div>

      {/* Usage Examples Collapsible */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setUsageOpen((prev) => !prev)}
          className="w-full flex items-center gap-2 px-4 py-2 text-left text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <span
            className="transition-transform duration-200"
            style={{ display: 'inline-block', transform: usageOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}
          >
            &#9654;
          </span>
          <span>📖</span>
          <span>Usage Examples</span>
        </button>

        {usageOpen && (
          <div className="px-4 pb-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Enter the following prompt to the chatbot:
            </p>
            <pre className="bg-gray-900 dark:bg-gray-950 text-gray-100 text-sm font-mono p-4 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed border border-gray-700">
              {USAGE_EXAMPLE}
            </pre>
          </div>
        )}
      </div>

      {/* Main 2x2 Grid */}
      <div className="flex-1 grid grid-cols-2 gap-0 overflow-hidden">
        {/* Top Left: Chat Panel */}
        <div className="col-span-1 row-span-1 border-r border-b border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col">
          <ChatPanel />
        </div>

        {/* Top Right: Plan/Code/Template Panel */}
        <div className="col-span-1 row-span-1 border-b border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col">
          <PlanCodePanel
            activeTab={activeTab}
            onTabChange={setActiveTab}
            plan={plan}
            intent={intent}
            isExecuting={isExecuting}
            onExecute={handleExecute}
            code={currentCode}
            onRerun={handleRerun}
            isRerunning={isRerunning}
            codeError={codeError}
            onSaveTemplate={handleSaveTemplate}
            canSaveTemplate={canSaveTemplate}
            isSaving={isSavingTemplate}
            savedTemplateCount={savedTemplates.length}
            savedTemplates={savedTemplates}
            onApplyTemplate={handleApplyTemplate}
          />
        </div>

        {/* Bottom Left: Data Panel */}
        <div className="col-span-1 row-span-1 border-r border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col">
          <DataPanel />
        </div>

        {/* Bottom Right: Report Panel */}
        <div className="col-span-1 row-span-1 overflow-hidden flex flex-col">
          <ReportPanel
            reportCharts={reportCharts}
            reportText={reportText}
            isLoading={isExecuting}
          />
        </div>
      </div>
    </div>
  )
}
