import createClient, { type Middleware } from 'openapi-fetch'

import { getStoredSession, storeSession } from '../auth/session'
import type { paths } from './schema'

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

/** Typed client for the ReturnRight API. Types come from src/api/schema.d.ts (npm run gen:api). */
export const api = createClient<paths>({ baseUrl: apiBaseUrl })

/** Turns a path the API returns, such as a photo_url, into a URL the browser can load. */
export function apiAssetUrl(path: string): string {
  return /^https?:\/\//.test(path) ? path : `${apiBaseUrl}${path}`
}

const authHeader: Middleware = {
  onRequest({ request }) {
    const token = getStoredSession()?.token
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  // A staff token that expired or was revoked: drop the session and go to the login page.
  onResponse({ request, response }) {
    const staffCall = request.headers.has('Authorization')
    if (response.status === 401 && staffCall && !request.url.endsWith('/auth/login')) {
      storeSession(null)
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
    return response
  },
}

api.use(authHeader)
