/**
 * Mock copies of the business rules in src/api/returnright/domain. The API is the source of
 * truth; these exist only so the UI can be demoed before it is ready.
 */
import type { Grade, ItemDecision } from '../types'

export const RETURN_WINDOW_DAYS = 30
export const ELECTRONICS_WINDOW_DAYS = 10
export const NEVER_RETURNABLE = ['Innerwear', 'Perishables']
export const APPROVAL_THRESHOLD = 10_000
export const FLAG_RETURNS_IN_30_DAYS = 3

const DAY_MS = 86_400_000

export function daysBetween(fromIso: string, to: Date): number {
  const from = new Date(fromIso)
  const a = Date.UTC(from.getFullYear(), from.getMonth(), from.getDate())
  const b = Date.UTC(to.getFullYear(), to.getMonth(), to.getDate())
  return Math.round((b - a) / DAY_MS)
}

export function addDays(iso: string, days: number): string {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

/** Window starts on the delivery date; the last day is allowed (day 30 ok, day 31 refused). */
export function checkEligibility(
  category: string,
  deliveredOn: string | null,
  today: Date,
): { eligible: boolean; reason: string; windowEndsOn: string | null } {
  if (NEVER_RETURNABLE.includes(category)) {
    return {
      eligible: false,
      reason: `${category} items cannot be returned for hygiene and safety reasons.`,
      windowEndsOn: null,
    }
  }
  if (!deliveredOn) {
    return { eligible: false, reason: 'This item has not been delivered yet.', windowEndsOn: null }
  }
  const windowDays = category === 'Electronics' ? ELECTRONICS_WINDOW_DAYS : RETURN_WINDOW_DAYS
  const windowEndsOn = addDays(deliveredOn, windowDays)
  const day = daysBetween(deliveredOn, today)
  if (day > windowDays) {
    return {
      eligible: false,
      reason: `The ${windowDays}-day return window for ${category.toLowerCase()} closed. Today is day ${day} after delivery.`,
      windowEndsOn,
    }
  }
  return {
    eligible: true,
    reason: `Returnable until day ${windowDays} after delivery (day ${day} today).`,
    windowEndsOn,
  }
}

/** Grades A and B refund 100%, grade C refunds 50%, rejected items refund nothing. */
export function refundFor(
  unitPrice: number,
  quantity: number,
  grade: Grade,
  decision: ItemDecision,
) {
  if (decision === 'reject') return 0
  const share = grade === 'C' ? 0.5 : 1
  return Math.round(unitPrice * quantity * share * 100) / 100
}

/** Strictly above 10,000 INR for the whole return. */
export const needsApproval = (total: number) => total > APPROVAL_THRESHOLD

export const toMoney = (n: number) => n.toFixed(2)
