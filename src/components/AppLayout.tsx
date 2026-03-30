'use client'

import React, { useState, useCallback, useEffect } from 'react'
import { useApi } from '@/hooks/useApi'
import { ReportData, TemplateItem, TemplatesData } from '@/types/api'
import ChatPanel from './ChatPanel'
import PlanCodePanel from './PlanCodePanel'
import DataPanel from './DataPanel'
import ReportPanel from './ReportPanel'

export default function AppLayout() {
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
    <div className="grid grid-cols-2 gap-0 h-screen bg-white overflow-hidden">
      {/* Top Left: Chat Panel (25% width) */}
      <div className="col-span-1 row-span-1 border-r border-b border-gray-200 overflow-hidden flex flex-col">
        <ChatPanel />
      </div>

      {/* Top Right: Plan/Code/Template Panel (25% width) */}
      <div className="col-span-1 row-span-1 border-b border-gray-200 overflow-hidden flex flex-col">
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

      {/* Bottom Left: Data Panel (50% width) */}
      <div className="col-span-1 row-span-1 border-r border-gray-200 overflow-hidden flex flex-col">
        <DataPanel />
      </div>

      {/* Bottom Right: Report Panel (50% width) */}
      <div className="col-span-1 row-span-1 overflow-hidden flex flex-col">
        <ReportPanel
          reportCharts={reportCharts}
          reportText={reportText}
          isLoading={isExecuting}
        />
      </div>
    </div>
  )
}
