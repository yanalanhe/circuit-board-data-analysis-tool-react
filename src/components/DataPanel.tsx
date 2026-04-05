'use client'

import React, { useState, useCallback } from 'react'
import FileUploadArea from './FileUploadArea'
import DataGrid from './DataGrid'
import { useFileUpload } from '@/hooks/useFileUpload'
import { useDataPreview } from '@/hooks/useDataPreview'
import { useApi } from '@/hooks/useApi'

export default function DataPanel() {
  const { upload, isLoading, error, filenames, rowCounts, largeDataWarning } =
    useFileUpload()
  const { files: previewFiles, isLoading: previewLoading, error: previewError, refetch } = useDataPreview()
  const { session_id, apiCall } = useApi()
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [activeFile, setActiveFile] = useState<string | null>(null)
  const [cellSaveError, setCellSaveError] = useState<string | null>(null)
  const [isDownsampling, setIsDownsampling] = useState(false)
  const [downsampleError, setDownsampleError] = useState<string | null>(null)
  const [downsampleSuccess, setDownsampleSuccess] = useState(false)

  const handleFilesSelected = async (files: File[]) => {
    setUploadError(null)
    const result = await upload(files)
    if (result) {
      // Set first file as active and refetch preview
      setActiveFile(result.filenames[0])
      await refetch()
    } else if (error) {
      setUploadError(error)
    }
  }

  const handleCellSave = useCallback(
    async (rowIndex: number, column: string, value: unknown) => {
      if (!activeFile) {
        throw new Error('No file selected')
      }

      setCellSaveError(null)

      try {
        const response = await apiCall('/api/data', 'PUT', {
          session_id,
          updates: {
            filename: activeFile,
            row_index: rowIndex,
            column,
            value,
          },
        })

        if (response.status !== 'success') {
          throw new Error(response.error?.message || 'Failed to save cell')
        }

        // Refetch the data to get the updated preview
        await refetch()
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to save cell'
        setCellSaveError(errorMessage)
        throw new Error(errorMessage)
      }
    },
    [activeFile, session_id, apiCall, refetch]
  )

  const handleDownsample = async () => {
    setIsDownsampling(true)
    setDownsampleError(null)
    try {
      const response = await apiCall('/api/downsample', 'POST')
      if (response.status === 'error') {
        setDownsampleError(response.error?.message || 'Downsampling failed')
      } else {
        setDownsampleSuccess(true)
        await refetch()
      }
    } catch {
      setDownsampleError('Downsampling failed. Please try again.')
    } finally {
      setIsDownsampling(false)
    }
  }

  const hasUploadedFiles = filenames.length > 0

  // Set initial active file if not set
  React.useEffect(() => {
    if (filenames.length > 0 && !activeFile) {
      setActiveFile(filenames[0])
    }
  }, [filenames, activeFile])

  // Get active file preview
  const activeFilePreview = activeFile
    ? previewFiles.find((f) => f.name === activeFile)
    : null

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-3 flex-shrink-0">
        <h2 className="font-bold text-sm text-gray-900 dark:text-gray-100">Data</h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col">
        {/* Error Messages */}
        {(uploadError || error) && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            <p className="font-medium">Upload Error</p>
            <p>{uploadError || error}</p>
          </div>
        )}

        {cellSaveError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            <p className="font-medium">Save Error</p>
            <p>{cellSaveError}</p>
            <button
              onClick={() => setCellSaveError(null)}
              className="text-xs text-red-600 hover:text-red-800 underline mt-2"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Large Data Warning */}
        {largeDataWarning && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm">
            <p className="font-medium">⚠️ Large Dataset Warning</p>
            <p>{largeDataWarning.message}</p>
            <div className="mt-3 flex flex-col gap-2">
              <div className="flex gap-2">
                {!downsampleSuccess ? (
                  <>
                    <button
                      onClick={handleDownsample}
                      disabled={isDownsampling}
                      className={`px-3 py-1.5 bg-yellow-100 border border-yellow-300 rounded text-yellow-800 text-xs font-medium ${
                        isDownsampling ? 'opacity-60 cursor-not-allowed' : 'hover:bg-yellow-200 cursor-pointer'
                      }`}
                    >
                      {isDownsampling ? 'Downsampling…' : 'Auto-downsample to 10,000 points'}
                    </button>
                    {downsampleError && (
                      <p className="text-xs text-red-600 mt-1">{downsampleError}</p>
                    )}
                  </>
                ) : (
                  <p className="text-xs text-green-700 font-medium">
                    ✓ Dataset downsampled to 10,000 rows — analysis ready
                  </p>
                )}
              </div>
              <p className="text-xs text-yellow-600">
                Or filter your data directly in the table below, then run analysis on the reduced dataset.
              </p>
            </div>
          </div>
        )}

        {!hasUploadedFiles ? (
          <div className="flex-1 flex flex-col items-center justify-center">
            <FileUploadArea
              onFilesSelected={handleFilesSelected}
              isLoading={isLoading}
            />
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Tabs for multiple files */}
            {filenames.length > 0 && (
              <div className="flex gap-2 mb-3 border-b border-gray-200 overflow-x-auto flex-shrink-0">
                {filenames.map((filename) => (
                  <button
                    key={filename}
                    onClick={() => setActiveFile(filename)}
                    className={`px-3 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                      activeFile === filename
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {filename}
                    <span className="text-xs text-gray-500 ml-2">
                      ({rowCounts[filename]?.toLocaleString() || 0})
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Data Grid or Loading State */}
            <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
              {previewLoading ? (
                <div className="flex items-center justify-center h-64 text-gray-500">
                  Loading data preview...
                </div>
              ) : previewError ? (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                  <p className="font-medium">Preview Error</p>
                  <p>{previewError}</p>
                </div>
              ) : activeFilePreview ? (
                <DataGrid
                  columns={activeFilePreview.columns}
                  dtypes={activeFilePreview.dtypes}
                  rows={activeFilePreview.preview}
                  onCellSave={handleCellSave}
                />
              ) : (
                <div className="flex items-center justify-center h-64 text-gray-500">
                  No data available for selected file
                </div>
              )}
            </div>

            {/* Upload More Button */}
            <div className="mt-4 pt-4 border-t border-gray-200 flex-shrink-0">
              <button
                onClick={() => setActiveFile(null)}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Upload More Files
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
