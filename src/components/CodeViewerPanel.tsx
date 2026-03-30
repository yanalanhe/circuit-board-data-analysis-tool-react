'use client'

import React, { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'

// Wrap Monaco in a dynamic import with SSR disabled to avoid hydration errors in Next.js 14
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center">
      <p className="text-gray-400 text-sm">Loading editor…</p>
    </div>
  ),
})

interface CodeViewerPanelProps {
  code: string | null
  onRerun?: (code: string) => void
  isRerunning?: boolean
  codeError?: string | null
}

export default function CodeViewerPanel({
  code,
  onRerun,
  isRerunning = false,
  codeError = null,
}: CodeViewerPanelProps) {
  const [editedCode, setEditedCode] = useState(code ?? '')

  // Sync editedCode when a new analysis result arrives (code prop changes from AppLayout)
  useEffect(() => {
    setEditedCode(code ?? '')
  }, [code])

  if (!code && !editedCode) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-gray-500 text-sm italic">
          Run an analysis to see the generated code here
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Re-run toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <button
          onClick={() => onRerun?.(editedCode)}
          disabled={!editedCode || isRerunning}
          className="px-3 py-1 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRerunning ? 'Running…' : 'Re-run'}
        </button>
        {isRerunning && (
          <span className="text-xs text-gray-500">Executing edited code…</span>
        )}
      </div>

      {/* Inline validation error — shown only for VALIDATION_ERROR, not execution errors */}
      {codeError && (
        <div className="px-3 py-2 bg-red-50 border-b border-red-200 flex-shrink-0">
          <p className="text-sm text-red-700 whitespace-pre-wrap">{codeError}</p>
        </div>
      )}

      {/* Editable Monaco editor */}
      <div className="flex-1 overflow-hidden">
        <MonacoEditor
          height="100%"
          language="python"
          theme="vs"
          value={editedCode}
          onChange={(value) => setEditedCode(value ?? '')}
          options={{
            readOnly: false,
            wordWrap: 'off',
            minimap: { enabled: false },
            fontSize: 13,
            lineHeight: 1.4,
            fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, monospace',
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  )
}
