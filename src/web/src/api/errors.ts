import type { ErrorResponse } from './types'

/** Error thrown by every backend call. `code` matches ErrorResponse.code from the API. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly requestId: string | null

  constructor(status: number, body: ErrorResponse) {
    super(body.message)
    this.name = 'ApiError'
    this.code = body.code
    this.status = status
    this.requestId = body.request_id ?? null
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error && error.message) return error.message
  return 'Something went wrong. Please try again.'
}
