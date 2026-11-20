import type {
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
  damaged: 'Damaged or defective',
  wrong_item: 'Wrong item sent',
  not_as_described: 'Not as described',
  size_or_fit: 'Size or fit',
  no_longer_needed: 'No longer needed',
  other: 'Other',
}

export const REFUND_METHOD_LABEL: Record<RefundMethod, string> = {
  original_payment: 'Original payment method',
  store_credit: 'Store credit',
}

export const REFUND_STATUS_LABEL: Record<RefundStatus, string> = {
  pending_approval: 'Awaiting approval',
  approved: 'Approved',
  processing: 'Processing',
  paid: 'Paid',
  failed: 'Failed',
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
  gateway_refund: 'Gateway refund',
  store_credit: 'Store credit',
}
