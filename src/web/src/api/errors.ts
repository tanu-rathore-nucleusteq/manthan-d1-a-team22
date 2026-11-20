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

const FALLBACK: Record<number, string> = {
  401: 'Your session has ended. Sign in again.',
  403: "Your role can't use this screen.",
  404: "We couldn't find that.",
  413: 'That photo is too large. Use one under 5 MB.',
  501: 'This part of ReturnRight is not available yet.',
}

/**
 * Builds an ApiError from any error body the API sends:
 * `{ code, message }` for business rules, `{ detail: string }` for auth and stubs,
 * and `{ detail: [{ loc, msg }] }` for validation.
 */
export function toApiError(status: number, body: unknown): ApiError {
  const b = (body && typeof body === 'object' ? body : {}) as {
    code?: string
    message?: string
    request_id?: string | null
    detail?: unknown
  }
  const code = b.code ?? `http_${status}`
  if (typeof b.message === 'string') {
    return new ApiError(status, { code, message: b.message, request_id: b.request_id })
  }
  if (typeof b.detail === 'string') return new ApiError(status, { code, message: b.detail })
  if (Array.isArray(b.detail) && b.detail.length > 0) {
    const first = b.detail[0] as { loc?: (string | number)[]; msg?: string }
    const field = first.loc?.filter((part) => part !== 'body').join('.')
    const message = first.msg ? (field ? `${field}: ${first.msg}` : first.msg) : 'Check the form.'
    return new ApiError(status, { code: 'validation_error', message })
  }
  const message =
    FALLBACK[status] ??
    (status >= 500 ? 'The server had a problem. Try again in a moment.' : 'Something went wrong.')
  return new ApiError(status, { code, message })
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  // fetch rejects with a TypeError when the API can't be reached at all.
  if (error instanceof TypeError)
    return "Can't reach the ReturnRight service. Check your connection and try again."
  if (error instanceof Error && error.message) return error.message
  return 'Something went wrong. Please try again.'
}
