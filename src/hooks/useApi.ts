'use client'

import { useContext } from 'react'
import { SessionContext } from '@/lib/SessionContext'
import { ApiResponse, UseApiReturn } from '@/types/api'

/**
 * useApi Hook
 * Provides session_id and apiCall function for backend communication
 * Automatically includes session_id in all requests
 */
export function useApi(): UseApiReturn {
  const context = useContext(SessionContext)

  if (!context) {
    throw new Error(
      'useApi must be used within SessionProvider. Make sure your app is wrapped with <SessionProvider>'
    )
  }

  const { sessionId, apiCall } = context

  // Task 3.1: Execute analysis function
  const executeAnalysis = async (): Promise<void> => {
    try {
      const response = await apiCall(
        '/api/execute',
        'POST',
        { session_id: sessionId }
      )

      if (response.status === 'error') {
        throw new Error(response.error?.message || 'Execute failed')
      }

      // Pipeline execution started successfully
      return response.data
    } catch (error) {
      console.error('Execute failed:', error)
      throw error
    }
  }

  return {
    session_id: sessionId,
    apiCall: async <T = any,>(
      endpoint: string,
      method: 'GET' | 'POST' | 'PUT' | 'DELETE',
      body?: any
    ): Promise<ApiResponse<T>> => {
      return apiCall<T>(endpoint, method, body)
    },
    executeAnalysis, // Task 3.1: Add execute function
  }
}
