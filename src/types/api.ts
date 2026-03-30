/**
 * API Response Types
 * Standard format for all backend API responses
 */

export interface ApiResponse<T = any> {
  status: 'success' | 'error'
  data?: T
  error?: {
    message: string
    code?: string
  }
}

/**
 * Session-related types
 */
export interface SessionData {
  session_id: string
}

export type SessionResponse = ApiResponse<SessionData>

/**
 * useApi hook return type
 */
export interface UseApiReturn {
  session_id: string
  apiCall: <T = any>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    body?: any
  ) => Promise<ApiResponse<T>>
  executeAnalysis?: () => Promise<any> // Task 3.1: Execute analysis function
}

/**
 * Report data returned by GET /api/report
 */
export interface ReportData {
  charts: string[]  // base64-encoded PNG strings (FastAPI serializes list[bytes] → base64)
  text: string      // trend analysis text (may be empty string)
  code: string      // generated Python code
}

/**
 * Template types for Story 11.1
 */
export interface TemplateItem {
  name: string
  plan: string[]
  code: string
}

export interface TemplatesData {
  templates: TemplateItem[]
}
