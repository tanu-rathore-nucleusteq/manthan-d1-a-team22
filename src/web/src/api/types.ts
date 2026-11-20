/**
 * Wire types for the ReturnRight API. They mirror src/api/returnright/dtos field for field,
 * so names stay snake_case. Once the API is running, `npm run gen:api` produces the same
 * shapes in schema.d.ts; switch imports there and delete this file.
 *
 * Fields marked PROPOSED are not in the backend DTOs yet. The UI needs them and treats
 * them as optional until the API adds them.
 */
import type { Role } from '../auth/roles'

/** Decimal in INR, serialised by Pydantic as a string such as "1299.00". Never parse to do maths on the server's behalf. */
export type Money = string

export type ReturnStatus =
  'requested' | 'approved' | 'in_transit' | 'received' | 'inspected' | 'refunded' | 'rejected'
export type Grade = 'A' | 'B' | 'C'
export type ItemDecision = 'accept' | 'reject'
export type RefundMethod = 'original_payment' | 'store_credit'
export type RefundStatus =
  'pending_approval' | 'approved' | 'processing' | 'paid' | 'failed' | 'rejected'
export type ReturnReason =
  'damaged' | 'wrong_item' | 'not_as_described' | 'size_or_fit' | 'no_longer_needed' | 'other'
export type LedgerEntryType = 'gateway_refund' | 'store_credit'

// ---- Common ---------------------------------------------------------------------------

export interface ErrorResponse {
  code: string
  message: string
  request_id?: string | null
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

// ---- Auth -----------------------------------------------------------------------------

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  role: Role
}

// ---- Orders ---------------------------------------------------------------------------

export interface OrderLookupRequest {
  order_number: string
  email: string
}

export interface ItemEligibilityResponse {
  order_item_id: number
  product_name: string
  category: string
  unit_price: Money
  quantity: number
  eligible: boolean
  reason: string
  window_ends_on?: string | null
}

export interface OrderLookupResponse {
  order_number: string
  delivered_on: string | null
  items: ItemEligibilityResponse[]
}

// ---- Returns --------------------------------------------------------------------------

export interface ReturnItemRequest {
  order_item_id: number
  quantity: number
}

export interface CreateReturnRequest {
  order_number: string
  email: string
  items: ReturnItemRequest[]
  reason: ReturnReason
  reason_details?: string | null
  refund_method: RefundMethod
}

export interface CustomerProofRequest {
  email: string
}

export interface StatusEventResponse {
  status: ReturnStatus
  at: string
  note?: string | null
}

export interface ReturnItemResponse {
  return_item_id: number
  product_name: string
  quantity: number
  grade?: Grade | null
  decision?: ItemDecision | null
  refund_amount?: Money | null
  /** PROPOSED: lets the warehouse screen preview the refund before submitting. */
  unit_price?: Money | null
}

export interface ReturnDetailResponse {
  return_code: string
  status: ReturnStatus
  reason: ReturnReason
  refund_method: RefundMethod
  items: ReturnItemResponse[]
  timeline: StatusEventResponse[]
  refund_total?: Money | null
  created_at: string
  /** PROPOSED: staff screens show these. */
  order_number?: string
  reason_details?: string | null
  photo_url?: string | null
  customer_name?: string
  customer_flagged?: boolean
}

export interface ReturnLabelResponse {
  return_code: string
  qr_svg: string
  ship_to: string
}

/** PROPOSED: one row of the warehouse queue (GET returns filtered by status). */
export interface ReturnSummaryResponse {
  return_code: string
  status: ReturnStatus
  customer_name: string
  item_count: number
  refund_total: Money | null
  created_at: string
  updated_at: string
}

// ---- Warehouse ------------------------------------------------------------------------

export interface ItemInspectionRequest {
  return_item_id: number
  grade: Grade
  decision: ItemDecision
  notes?: string | null
}

export interface InspectionRequest {
  items: ItemInspectionRequest[]
}

export interface InspectionResultResponse {
  return_code: string
  status: ReturnStatus
  items: ReturnItemResponse[]
  refund_total: Money
  needs_finance_approval: boolean
}

// ---- Finance --------------------------------------------------------------------------

export interface ApprovalDecisionRequest {
  approve: boolean
  comment?: string | null
}

export interface RefundResponse {
  refund_id: number
  return_code: string
  return_item_id: number
  amount: Money
  method: RefundMethod
  status: RefundStatus
  gateway_transaction_id?: string | null
  approved_by?: string | null
  created_at: string
}

export interface PendingApprovalResponse {
  return_code: string
  customer_flagged: boolean
  refund_total: Money
  refunds: RefundResponse[]
}

export interface LedgerEntryResponse {
  entry_id: number
  refund_id: number
  entry_type: LedgerEntryType
  amount: Money
  created_at: string
}

// ---- Dashboard ------------------------------------------------------------------------

export interface CategoryReturnRateResponse {
  category: string
  orders: number
  returns: number
  return_rate: number
}

export interface ReasonCountResponse {
  reason: ReturnReason
  count: number
}

export interface FlaggedCustomerResponse {
  customer_id: number
  name: string
  returns_last_30_days: number
}

export interface DashboardResponse {
  return_rate_by_category: CategoryReturnRateResponse[]
  top_reasons: ReasonCountResponse[]
  average_cycle_time_hours: number | null
  flagged_customers: FlaggedCustomerResponse[]
  generated_at: string
}
