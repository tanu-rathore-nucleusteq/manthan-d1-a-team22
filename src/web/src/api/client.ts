import createClient, { type Middleware } from 'openapi-fetch'

import { getStoredSession } from '../auth/session'
import type { paths } from './schema'

/** Typed client for the ReturnRight API. Types come from src/api/schema.d.ts (npm run gen:api). */
export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
})

const authHeader: Middleware = {
  onRequest({ request }) {
    const token = getStoredSession()?.token
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
}

api.use(authHeader)
