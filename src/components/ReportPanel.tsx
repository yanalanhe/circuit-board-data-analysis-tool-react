'use client'

import React from 'react'

interface ReportPanelProps {
  reportCharts: string[]     // base64 PNG strings from /api/report → data.charts
  reportText: string | null  // trend analysis text from /api/report → data.text
  isLoading: boolean         // true while executeAnalysis() is running
}

export default function ReportPanel({
  reportCharts,
  reportText,
  isLoading,
}: ReportPanelProps) {
  const hasReport = reportCharts.length > 0 || !!reportText

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-3 flex-shrink-0">
        <h2 className="font-bold text-sm text-gray-900 dark:text-gray-100">Report</h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="mb-4 text-4xl text-gray-300 animate-pulse">⏳</div>
            <p className="text-gray-700 dark:text-gray-300 font-medium">Generating report…</p>
            <p className="text-gray-500 dark:text-gray-400 text-sm mt-2">
              Running analysis pipeline
            </p>
          </div>
        )}

        {/* Placeholder — no report, not loading */}
        {!isLoading && !hasReport && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="mb-4 text-4xl text-gray-300">📊</div>
            <p className="text-gray-700 dark:text-gray-300 font-medium">
              Run an analysis to see results here
            </p>
            <p className="text-gray-500 dark:text-gray-400 text-sm mt-2">
              Charts and trend analysis will display here
            </p>
          </div>
        )}

        {/* Report content */}
        {!isLoading && hasReport && (
          <div className="flex flex-col gap-6">
            {/* Charts */}
            {reportCharts.length > 0 && (
              <div className="flex flex-col gap-4">
                {reportCharts.map((chart, index) => (
                  <React.Fragment key={index}>
                    {/* eslint-disable-next-line @next/next/no-img-element -- base64 data URIs are not supported by next/image */}
                    <img
                      src={`data:image/png;base64,${chart}`}
                      alt={`Chart ${index + 1}`}
                      className="max-w-full h-auto rounded border border-gray-200"
                    />
                  </React.Fragment>
                ))}
              </div>
            )}

            {/* Trend analysis text */}
            {reportText && (
              <div className="border-t border-gray-100 pt-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Analysis
                </h3>
                <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                  {reportText}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
