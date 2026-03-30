'use client'

import React, { createContext, useState, useEffect, ReactNode } from 'react'
import { ApiResponse, SessionResponse } from '@/types/api'

interface SessionContextValue {
  sessionId: string
  apiCall: <T = any>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    body?: any
  ) => Promise<ApiResponse<T>>
}

export const SessionContext = createContext<SessionContextValue | null>(null)

interface SessionProviderProps {
  children: ReactNode
}

export function SessionProvider({ children }: SessionProviderProps) {
  const [sessionId, setSessionId] = useState<string>('')

  // Initialize session on mount
  useEffect(() => {
    const initializeSession = async () => {
      // Generate UUID v4
      const uuid = crypto.randomUUID()
      setSessionId(uuid)

      // Call backend to create session
      try {
        const response = await fetch('/api/session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': uuid,
          },
          body: JSON.stringify({}),
        })
        const data: SessionResponse = await response.json()
        if (data.status === 'success' && data.data?.session_id) {
          // Session created successfully - sessionId already set locally
          console.log('Session initialized:', data.data.session_id)
        }
      } catch (error) {
        console.error('Failed to initialize session:', error)
      }
    }

    initializeSession()
  }, [])

  const apiCall = async <T = any,>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    body?: any
  ): Promise<ApiResponse<T>> => {
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
      }

      const fetchOptions: RequestInit = {
        method,
        headers,
      }

      if (method !== 'GET' && body) {
        fetchOptions.body = JSON.stringify(body)
      }

      const response = await fetch(endpoint, fetchOptions)
      const data: ApiResponse<T> = await response.json()

      return data
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred'
      return {
        status: 'error',
        error: {
          message: errorMessage,
          code: 'NETWORK_ERROR',
        },
      }
    }
  }

  return (
    <SessionContext.Provider value={{ sessionId, apiCall }}>
      {children}
    </SessionContext.Provider>
  )
}
