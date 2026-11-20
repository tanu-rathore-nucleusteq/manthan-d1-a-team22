import type { ReturnRightBackend } from './backend'
import { api, apiBaseUrl } from './client'
import { toApiError } from './errors'

/** Unwraps an openapi-fetch result, turning any non-2xx answer into an ApiError. */
async function call<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>) {
  const { data, error, response } = await request
  if (!response.ok || data === undefined) throw toApiError(response.status, error)
  return data
}

const customer = (email: string) => ({ 'X-Customer-Email': email })

/** Largest page the API serves; the queues are short, so one page holds them all. */
const ALL = { page: 1, size: 100 }

/**
 * The live ReturnRight API (docs/api.md). Every implemented endpoint the screens use is
 * called here; the dashboard is still a stub on the server, so it stays on the mock.
 */
export function createHttpBackend(
  dashboard: ReturnRightBackend['getDashboard'],
): ReturnRightBackend {
  return {
    login: (body) => call(api.POST('/api/v1/auth/login', { body })),

    // PROVISIONAL path and body until the API publishes the signup endpoint in openapi.json.
    async signup(body) {
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!response.ok) throw toApiError(response.status, await response.json().catch(() => null))
    },

    lookupOrder: (body) => call(api.POST('/api/v1/orders/lookup', { body })),

    createReturn: (body) => call(api.POST('/api/v1/returns', { body })),

    // multipart/form-data: posted with fetch so the browser sets the boundary itself.
    async uploadReturnPhoto(returnCode, email, returnItemId, photo) {
      const form = new FormData()
      form.append('email', email)
      form.append('return_item_id', String(returnItemId))
      form.append('photo', photo)
      const response = await fetch(
        `${apiBaseUrl}/api/v1/returns/${encodeURIComponent(returnCode)}/photo`,
        { method: 'POST', body: form },
      )
      if (!response.ok) throw toApiError(response.status, await response.json().catch(() => null))
    },

    getReturn: (returnCode, { email }) =>
      call(
        api.GET('/api/v1/returns/{return_code}', {
          params: { path: { return_code: returnCode }, header: customer(email) },
        }),
      ),

    getLabel: (returnCode, { email }) =>
      call(
        api.GET('/api/v1/returns/{return_code}/label', {
          params: { path: { return_code: returnCode }, header: customer(email) },
        }),
      ),

    markShipped: (returnCode, body) =>
      call(
        api.POST('/api/v1/returns/{return_code}/ship', {
          params: { path: { return_code: returnCode } },
          body,
        }),
      ),

    listWarehouseQueue: (status) =>
      call(api.GET('/api/v1/warehouse/returns', { params: { query: { status, ...ALL } } })),

    getReturnForStaff: (returnCode) =>
      call(
        api.GET('/api/v1/warehouse/returns/{return_code}', {
          params: { path: { return_code: returnCode } },
        }),
      ),

    markReceived: (returnCode) =>
      call(
        api.POST('/api/v1/warehouse/returns/{return_code}/receive', {
          params: { path: { return_code: returnCode } },
        }),
      ),

    inspectReturn: (returnCode, body) =>
      call(
        api.POST('/api/v1/warehouse/returns/{return_code}/inspection', {
          params: { path: { return_code: returnCode } },
          body,
        }),
      ),

    listPendingApprovals: async () =>
      (await call(api.GET('/api/v1/finance/approvals', { params: { query: ALL } }))).items,

    decideApproval: (returnCode, body) =>
      call(
        api.POST('/api/v1/finance/approvals/{return_code}/decision', {
          params: { path: { return_code: returnCode } },
          body,
        }),
      ),

    async listLedger() {
      // The ledger screen shows totals, so it needs every entry, not only the first page.
      const first = await call(api.GET('/api/v1/finance/ledger', { params: { query: ALL } }))
      const items = [...first.items]
      for (let page = 2; items.length < first.total; page++) {
        const next = await call(
          api.GET('/api/v1/finance/ledger', { params: { query: { ...ALL, page } } }),
        )
        if (next.items.length === 0) break
        items.push(...next.items)
      }
      return { ...first, items, size: items.length }
    },

    getDashboard: dashboard,
  }
}
