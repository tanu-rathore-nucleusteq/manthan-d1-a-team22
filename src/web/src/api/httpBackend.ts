import { getStoredSession } from '../auth/session'
import type { ReturnRightBackend } from './backend'
import { ApiError } from './errors'
import type {
  DashboardResponse,
  ErrorResponse,
  InspectionResultResponse,
  LedgerEntryResponse,
  OrderLookupResponse,
  PageResponse,
  PendingApprovalResponse,
  ReasonCountResponse,
  RefundMethod,
  ReturnDetailResponse,
  ReturnItemResponse,
  ReturnLabelResponse,
  ReturnReason,
  ReturnSummaryResponse,
  TokenResponse,
} from './types'

const ORIGIN = import.meta.env.VITE_API_BASE_URL ?? ''
const API_ROOT = `${ORIGIN}/api/v1`
/** Lists are paged by the API; the screens show one page, so ask for the largest one. */
const PAGE_SIZE = '100'

// ---- Wire shapes that differ from the UI types ------------------------------------------

type ApiReturnReason =
  'damaged' | 'wrong_item' | 'size' | 'not_as_described' | 'changed_mind' | 'quality' | 'other'

/** The API keeps the reason and photos per item; the UI shows them once per return. */
type ApiReturnItem = ReturnItemResponse & {
  order_item_id: number
  reason: ApiReturnReason
  reason_details?: string | null
  photo_urls: string[]
}

type ApiReturnDetail = Omit<ReturnDetailResponse, 'reason' | 'items'> & { items: ApiReturnItem[] }

type ApiLedgerEntry = Omit<LedgerEntryResponse, 'entry_type'> & {
  entry_type: 'refund' | 'reversal'
  method: RefundMethod
}

type ApiDashboard = Omit<DashboardResponse, 'top_reasons'> & {
  top_reasons: { reason: ApiReturnReason; count: number }[]
}

const API_REASON: Record<ReturnReason, ApiReturnReason> = {
  damaged: 'damaged',
  wrong_item: 'wrong_item',
  not_as_described: 'not_as_described',
  size_or_fit: 'size',
  no_longer_needed: 'changed_mind',
  other: 'other',
}

const UI_REASON: Record<ApiReturnReason, ReturnReason> = {
  damaged: 'damaged',
  wrong_item: 'wrong_item',
  size: 'size_or_fit',
  not_as_described: 'not_as_described',
  changed_mind: 'no_longer_needed',
  quality: 'other',
  other: 'other',
}

// ---- HTTP -------------------------------------------------------------------------------

interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  /** Customer GETs prove ownership with this header instead of a login. */
  email?: string
  query?: Record<string, string>
}

const FALLBACK_ERROR: Record<number, ErrorResponse> = {
  401: { code: 'unauthorized', message: 'Please sign in again to continue.' },
  403: { code: 'forbidden', message: "Your role doesn't have access to this page." },
  422: {
    code: 'validation_error',
    message: 'Some details are missing or invalid. Please check them and try again.',
  },
}

/** Turns any error body into the ApiError the screens already handle. */
function toApiError(status: number, data: unknown): ApiError {
  const body = (data ?? {}) as Partial<ErrorResponse> & { detail?: unknown }
  if (body.code && body.message) return new ApiError(status, body as ErrorResponse)
  const detail = typeof body.detail === 'string' && body.detail ? body.detail : null
  return new ApiError(
    status,
    FALLBACK_ERROR[status] ?? {
      code: `http_${status}`,
      message: detail ?? 'Something went wrong. Please try again.',
    },
  )
}

async function request<T>(
  path: string,
  { method = 'GET', body, email, query }: RequestOptions = {},
): Promise<T> {
  const headers = new Headers()
  const token = getStoredSession()?.token
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (email) headers.set('X-Customer-Email', email)
  let payload: BodyInit | undefined
  if (body instanceof FormData) {
    payload = body
  } else if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
    payload = JSON.stringify(body)
  }
  const url = `${API_ROOT}${path}${query ? `?${new URLSearchParams(query)}` : ''}`

  let response: Response
  try {
    response = await fetch(url, { method, headers, body: payload })
  } catch {
    throw new ApiError(0, {
      code: 'network_error',
      message: "We couldn't reach ReturnRight. Check your connection and try again.",
    })
  }
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) throw toApiError(response.status, data)
  return data as T
}

const codePath = (code: string) => encodeURIComponent(code.trim().toUpperCase())

// ---- Mapping ----------------------------------------------------------------------------

function toDetail(detail: ApiReturnDetail): ReturnDetailResponse {
  const first = detail.items[0]
  const photo = detail.items.flatMap((i) => i.photo_urls)[0]
  return {
    ...detail,
    reason: UI_REASON[first.reason],
    reason_details: first.reason_details ?? null,
    photo_url: photo ? `${ORIGIN}${photo}` : null,
  }
}

/** Several API reasons can share one UI label, so counts are merged after mapping. */
function toTopReasons(rows: ApiDashboard['top_reasons']): ReasonCountResponse[] {
  const counts = new Map<ReturnReason, number>()
  for (const { reason, count } of rows) {
    counts.set(UI_REASON[reason], (counts.get(UI_REASON[reason]) ?? 0) + count)
  }
  return [...counts].map(([reason, count]) => ({ reason, count })).sort((a, b) => b.count - a.count)
}

const staffDetail = async (code: string) =>
  toDetail(await request<ApiReturnDetail>(`/warehouse/returns/${codePath(code)}`))

// ---- Backend ----------------------------------------------------------------------------

export const httpBackend: ReturnRightBackend = {
  login: (body) => request<TokenResponse>('/auth/login', { method: 'POST', body }),

  lookupOrder: (body) => request<OrderLookupResponse>('/orders/lookup', { method: 'POST', body }),

  async createReturn({ reason, reason_details, items, ...body }) {
    const created = await request<ApiReturnDetail>('/returns', {
      method: 'POST',
      body: {
        ...body,
        items: items.map((item) => ({ ...item, reason: API_REASON[reason], reason_details })),
      },
    })
    return toDetail(created)
  },

  async uploadReturnPhoto(returnCode, email, photo) {
    const detail = await request<ApiReturnDetail>(`/returns/${codePath(returnCode)}`, { email })
    // The wizard takes one photo of the parcel; the API stores photos per item, so attach it to each.
    for (const item of detail.items) {
      const form = new FormData()
      form.append('email', email)
      form.append('return_item_id', String(item.return_item_id))
      form.append('photo', photo)
      await request(`/returns/${codePath(returnCode)}/photo`, { method: 'POST', body: form })
    }
  },

  getReturn: async (returnCode, { email }) =>
    toDetail(await request<ApiReturnDetail>(`/returns/${codePath(returnCode)}`, { email })),

  getLabel: (returnCode, { email }) =>
    request<ReturnLabelResponse>(`/returns/${codePath(returnCode)}/label`, { email }),

  markShipped: async (returnCode, { email }) =>
    toDetail(
      await request<ApiReturnDetail>(`/returns/${codePath(returnCode)}/ship`, {
        method: 'POST',
        body: { email },
      }),
    ),

  listWarehouseQueue: (status) =>
    request<PageResponse<ReturnSummaryResponse>>('/warehouse/returns', {
      query: { status, size: PAGE_SIZE },
    }),

  getReturnForStaff: staffDetail,

  markReceived: async (returnCode) =>
    toDetail(
      await request<ApiReturnDetail>(`/warehouse/returns/${codePath(returnCode)}/receive`, {
        method: 'POST',
      }),
    ),

  inspectReturn: (returnCode, body) =>
    request<InspectionResultResponse>(`/warehouse/returns/${codePath(returnCode)}/inspection`, {
      method: 'POST',
      body,
    }),

  async listPendingApprovals() {
    const page = await request<PageResponse<PendingApprovalResponse>>('/finance/approvals', {
      query: { size: PAGE_SIZE },
    })
    return page.items
  },

  async decideApproval(returnCode, body) {
    await request(`/finance/approvals/${codePath(returnCode)}/decision`, { method: 'POST', body })
    return staffDetail(returnCode)
  },

  async listLedger() {
    const page = await request<PageResponse<ApiLedgerEntry>>('/finance/ledger', {
      query: { size: PAGE_SIZE },
    })
    const items = page.items.map((entry): LedgerEntryResponse => ({
      ...entry,
      entry_type: entry.method === 'original_payment' ? 'gateway_refund' : 'store_credit',
    }))
    return { ...page, items }
  },

  async getDashboard() {
    const dashboard = await request<ApiDashboard>('/dashboard')
    return { ...dashboard, top_reasons: toTopReasons(dashboard.top_reasons) }
  },
}
