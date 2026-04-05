'use client'

import React, { useState } from 'react'

interface FileUploadAreaProps {
  onFilesSelected: (files: File[]) => void
  isLoading?: boolean
}

export default function FileUploadArea({
  onFilesSelected,
  isLoading = false,
}: FileUploadAreaProps) {
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (file) => file.type === 'text/csv' || file.name.endsWith('.csv')
    )

    if (droppedFiles.length > 0) {
      onFilesSelected(droppedFiles as File[])
    }
  }

  const handleBrowse = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files)
      if (selectedFiles.length > 0) {
        onFilesSelected(selectedFiles)
      }
    }
  }

  return (
    <div
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        dragActive ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30' : 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800'
      } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-blue-400'}`}
    >
      <input
        type="file"
        id="fileInput"
        multiple
        accept=".csv"
        onChange={handleBrowse}
        className="hidden"
        disabled={isLoading}
      />

      <label htmlFor="fileInput" className="block cursor-pointer">
        <div className="text-4xl mb-2">📁</div>
        <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-1">
          {isLoading ? 'Uploading...' : 'Drag and drop CSV files here'}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          or click to browse your computer
        </p>
        <button
          type="button"
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
          disabled={isLoading}
        >
          {isLoading ? 'Uploading...' : 'Browse Files'}
        </button>
      </label>
    </div>
  )
}
