'use client'

import { useState } from 'react'
import { useApi } from './useApi'
import { ApiResponse } from '@/types/api'

export interface UploadResponse {
  filenames: string[]
  row_counts: Record<string, number>
  large_data_warning?: {
    detected: boolean
    row_count: number
    size_mb: number
    message: string
  }
}

interface UseFileUploadReturn {
  upload: (files: File[]) => Promise<UploadResponse | null>
  isLoading: boolean
  error: string | null
  filenames: string[]
  rowCounts: Record<string, number>
  largeDataWarning: { detected: boolean; row_count: number; size_mb: number; message: string } | null
}

/**
 * useFileUpload Hook
 * Handles CSV file uploads to the backend via /api/upload endpoint
 */
export function useFileUpload(): UseFileUploadReturn {
  const { apiCall } = useApi()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filenames, setFilenames] = useState<string[]>([])
  const [rowCounts, setRowCounts] = useState<Record<string, number>>({})
  const [largeDataWarning, setLargeDataWarning] = useState<{
    detected: boolean
    row_count: number
    size_mb: number
    message: string
  } | null>(null)

  const upload = async (files: File[]): Promise<UploadResponse | null> => {
    setIsLoading(true)
    setError(null)

    try {
      // Create FormData for multipart/form-data upload
      const formData = new FormData()
      files.forEach((file) => {
        formData.append('files', file)
      })

      // Call the API
      const response: ApiResponse<UploadResponse> = await apiCall(
        '/api/upload',
        'POST',
        formData
      )

      if (response.status === 'error') {
        const errorMessage =
          response.error?.message || 'Failed to upload files'
        setError(errorMessage)
        return null
      }

      if (response.status === 'success' && response.data) {
        setFilenames(response.data.filenames)
        setRowCounts(response.data.row_counts)
        setLargeDataWarning(response.data.large_data_warning || null)
        return response.data
      }

      setError('Unexpected response from server')
      return null
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    upload,
    isLoading,
    error,
    filenames,
    rowCounts,
    largeDataWarning,
  }
}
