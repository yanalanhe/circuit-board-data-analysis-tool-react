'use client'

import { useState, useEffect } from 'react'
import { useApi } from './useApi'
import { ApiResponse } from '@/types/api'

export interface DataFilePreview {
  name: string
  columns: string[]
  dtypes: string[]
  rows: number
  preview: Record<string, unknown>[]
}

interface UseDataPreviewReturn {
  files: DataFilePreview[]
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * useDataPreview Hook
 * Fetches data preview from /api/data endpoint
 * Includes preview rows and column type information
 */
export function useDataPreview(): UseDataPreviewReturn {
  const { apiCall } = useApi()
  const [files, setFiles] = useState<DataFilePreview[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchPreview = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response: ApiResponse<{ files: DataFilePreview[] }> = await apiCall(
        '/api/data',
        'GET'
      )

      if (response.status === 'error') {
        const errorMessage = response.error?.message || 'Failed to load data preview'
        setError(errorMessage)
        setFiles([])
        return
      }

      if (response.status === 'success' && response.data) {
        setFiles(response.data.files)
      } else {
        setError('Unexpected response from server')
        setFiles([])
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      setFiles([])
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch preview on mount
  useEffect(() => {
    void fetchPreview()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    files,
    isLoading,
    error,
    refetch: fetchPreview,
  }
}
