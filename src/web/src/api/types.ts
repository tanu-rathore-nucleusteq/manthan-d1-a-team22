/**
 * Wire types for the ReturnRight API, taken from the generated OpenAPI schema
 * (src/api/schema.d.ts; regenerate with `npm run gen:api`). Names stay snake_case to
 * match the JSON. Never edit shapes here: change the API, then regenerate.
 */
import type { components } from './schema'

type Schemas = components['schemas']

/** Decimal in INR, serialised as a string such as "1299.00". Display it; never do maths on the server's behalf. */
export type Money = string

export type ReturnStatus = Schemas['ReturnStatus']
export type Grade = Schemas['Grade']
export type ItemDecision = Schemas['ItemDecision']
export type RefundMethod = Schemas['RefundMethod']
export type RefundStatus = Schemas['RefundStatus']
export type ReturnReason = Schemas['ReturnReason']
export type LedgerEntryType = Schemas['LedgerEntryType']

export type ErrorResponse = Schemas['ErrorResponse']
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export type LoginRequest = Schemas['LoginRequest']
export type TokenResponse = Schemas['TokenResponse']
export type UserResponse = Schemas['UserResponse']

export type OrderLookupRequest = Schemas['OrderLookupRequest']
export type ItemEligibilityResponse = Schemas['ItemEligibilityResponse']
export type OrderLookupResponse = Schemas['OrderLookupResponse']

export type ReturnItemRequest = Schemas['ReturnItemRequest']
export type CreateReturnRequest = Schemas['CreateReturnRequest']
export type CustomerProofRequest = Schemas['CustomerProofRequest']
export type StatusEventResponse = Schemas['StatusEventResponse']
export type ReturnItemResponse = Schemas['ReturnItemResponse']
export type ReturnDetailResponse = Schemas['ReturnDetailResponse']
export type ReturnLabelResponse = Schemas['ReturnLabelResponse']
export type ReturnSummaryResponse = Schemas['ReturnSummaryResponse']
export type PhotoUploadResponse = Schemas['PhotoUploadResponse']

export type ItemInspectionRequest = Schemas['ItemInspectionRequest']
export type InspectionRequest = Schemas['InspectionRequest']
export type InspectionResultResponse = Schemas['InspectionResultResponse']

export type ApprovalDecisionRequest = Schemas['ApprovalDecisionRequest']
export type RefundResponse = Schemas['RefundResponse']
export type PendingApprovalResponse = Schemas['PendingApprovalResponse']
export type LedgerEntryResponse = Schemas['LedgerEntryResponse']

export type CategoryReturnRateResponse = Schemas['CategoryReturnRateResponse']
export type ReasonCountResponse = Schemas['ReasonCountResponse']
export type FlaggedCustomerResponse = Schemas['FlaggedCustomerResponse']
export type DashboardResponse = Schemas['DashboardResponse']
