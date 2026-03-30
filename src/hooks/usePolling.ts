'use client'

import { useCallback, useRef } from 'react'
import { useApi } from '@/hooks/useApi'

/**
 * usePolling Hook
 *
 * Polls /api/status every 500ms until pipeline execution completes (running === false),
 * then calls onComplete callback.
 *
 * NOTE: The current backend /api/execute is synchronous — executeAnalysis() blocks until
 * the pipeline is done. This hook is created per architecture spec for when the backend
 * is converted to an async background task. Wire startPolling into handleExecute at
 * that point and remove the direct /api/report fetch from AppLayout.
 */
export function usePolling(onComplete: () => void) {
  const { apiCall } = useApi()
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    // Clear any existing interval before starting a new one
    stopPolling()

    intervalRef.current = setInterval(async () => {
      const response = await apiCall('/api/status', 'GET')
      if (response.status === 'success' && !response.data?.running) {
        stopPolling()
        onComplete()
      }
    }, 500)
  }, [apiCall, onComplete, stopPolling])

  return { startPolling, stopPolling }
}
