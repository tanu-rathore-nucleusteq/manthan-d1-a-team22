import type {
  Grade,
  LedgerEntryType,
  RefundMethod,
  RefundStatus,
  ReturnReason,
  ReturnStatus,
} from '../api/types'

export type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

export const STATUS_LABEL: Record<ReturnStatus, string> = {
  requested: 'Requested',
  approved: 'Approved',
  in_transit: 'In transit',
  received: 'Received',
  inspected: 'Inspected',
  refunded: 'Refunded',
  rejected: 'Rejected',
}

export const STATUS_TONE: Record<ReturnStatus, Tone> = {
  requested: 'neutral',
  approved: 'info',
  in_transit: 'info',
  received: 'warning',
  inspected: 'warning',
  refunded: 'success',
  rejected: 'danger',
}

/** Customer-facing order of the lifecycle; a return ends in Refunded or Rejected. */
export const STATUS_FLOW: ReturnStatus[] = [
  'requested',
  'approved',
  'in_transit',
  'received',
  'inspected',
  'refunded',
]

export const REASON_LABEL: Record<ReturnReason, string> = {
  damaged: 'Arrived damaged',
  wrong_item: 'Wrong item sent',
  size: 'Size or fit issue',
  not_as_described: 'Not as described',
  changed_mind: 'Changed my mind',
  quality: 'Poor quality',
  other: 'Other reason',
}

export const REFUND_METHOD_LABEL: Record<RefundMethod, string> = {
  original_payment: 'Original payment',
  store_credit: 'Store credit',
}

export const REFUND_STATUS_LABEL: Record<RefundStatus, string> = {
  pending_approval: 'Waiting for finance',
  approved: 'Approved',
  processing: 'Paying',
  paid: 'Paid',
  failed: 'Payment failed',
  rejected: 'Rejected',
}

export const REFUND_STATUS_TONE: Record<RefundStatus, Tone> = {
  pending_approval: 'warning',
  approved: 'info',
  processing: 'info',
  paid: 'success',
  failed: 'danger',
  rejected: 'danger',
}

export const LEDGER_TYPE_LABEL: Record<LedgerEntryType, string> = {
  refund: 'Refund',
  reversal: 'Reversal',
}

export const GRADE_LABEL: Record<Grade, string> = {
  A: 'Like new',
  B: 'Used, good',
  C: 'Damaged or incomplete',
}
