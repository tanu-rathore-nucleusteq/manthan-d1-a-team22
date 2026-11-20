import type { ReturnRightBackend } from '../backend'
import { ApiError } from '../errors'
import type {
  DashboardResponse,
  ItemEligibilityResponse,
  ReturnDetailResponse,
  ReturnReason,
  ReturnStatus,
  ReturnSummaryResponse,
} from '../types'
import { mockQrSvg } from './qr'
import {
  checkEligibility,
  FLAG_RETURNS_IN_30_DAYS,
  needsApproval,
  refundFor,
  toMoney,
} from './rules'
import {
  CATEGORY_ORDERS,
  createSeedState,
  CUSTOMERS,
  DEMO_PASSWORD,
  DEMO_STAFF,
  ORDERS,
  REASON_BASELINE,
  refundIdTail,
  type MockRefund,
  type MockReturn,
  type MockState,
} from './seed'

// v2: reasons, photos and ledger rows follow the live API contract.
const STORAGE_KEY = 'returnright.mock.v2'
const WAREHOUSE_ADDRESS =
  'ReturnRight Returns Centre, Plot 14, Sector 3, Pithampur, Madhya Pradesh 454775'

// ---- State (persisted in sessionStorage so a reload keeps the demo where it was) -------

let state: MockState = load()
/** Object URLs of uploaded photos, by return_item_id. Kept in memory only. */
const photos = new Map<number, string>()

function load(): MockState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw) as MockState
  } catch {
    // Storage unavailable: fall back to fresh seed data.
  }
  return createSeedState()
}

function save() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Storage full or blocked: the demo keeps working in memory.
  }
}

export function resetMockData() {
  state = createSeedState()
  photos.clear()
  save()
}

// ---- Helpers --------------------------------------------------------------------------

const delay = (min = 250, max = 650) =>
  new Promise((resolve) => setTimeout(resolve, min + Math.random() * (max - min)))

const fail = (status: number, code: string, message: string): never => {
  throw new ApiError(status, { code, message, request_id: `mock-${Date.now().toString(36)}` })
}

const now = () => new Date().toISOString()
const customerOf = (id: number) => CUSTOMERS.find((c) => c.customer_id === id)!
const sum = (values: number[]) => values.reduce((a, b) => a + b, 0)

function findReturn(code: string): MockReturn {
  const ret = state.returns.find((r) => r.return_code === code.trim().toUpperCase())
  return ret ?? fail(404, 'return_not_found', `No return found with code ${code.toUpperCase()}.`)
}

function requireProof(ret: MockReturn, email: string) {
  if (customerOf(ret.customer_id).email !== email.trim().toLowerCase()) {
    fail(404, 'return_not_found', 'No return matches that code and email.')
  }
}

function transition(ret: MockReturn, to: ReturnStatus, note: string | null = null) {
  const at = now()
  ret.status = to
  ret.updated_at = at
  ret.timeline.push({ status: to, at, note })
}

function returnsInLast30Days(customerId: number) {
  const since = Date.now() - 30 * 86_400_000
  return state.returns.filter(
    (r) => r.customer_id === customerId && new Date(r.created_at).getTime() >= since,
  ).length
}

const isFlagged = (customerId: number) => returnsInLast30Days(customerId) > FLAG_RETURNS_IN_30_DAYS

function toDetail(ret: MockReturn): ReturnDetailResponse {
  const refunds = state.refunds.filter((r) => r.return_code === ret.return_code)
  const graded = ret.items.some((i) => i.decision)
  return {
    return_code: ret.return_code,
    status: ret.status,
    refund_method: ret.refund_method,
    items: ret.items.map((i) => {
      const photo = photos.get(i.return_item_id)
      return {
        return_item_id: i.return_item_id,
        order_item_id: i.order_item_id,
        product_name: i.product_name,
        quantity: i.quantity,
        reason: ret.reason,
        reason_details: ret.reason_details,
        photo_urls: photo ? [photo] : [],
        grade: i.grade,
        decision: i.decision,
        refund_amount: i.refund_amount === null ? null : toMoney(i.refund_amount),
      }
    }),
    timeline: [...ret.timeline],
    refund_total: graded ? toMoney(sum(refunds.map((r) => r.amount))) : null,
    created_at: ret.created_at,
  }
}

function toSummary(ret: MockReturn): ReturnSummaryResponse {
  const refunds = state.refunds.filter((r) => r.return_code === ret.return_code)
  return {
    return_code: ret.return_code,
    status: ret.status,
    order_number: ret.order_number,
    customer_flagged: isFlagged(ret.customer_id),
    item_count: sum(ret.items.map((i) => i.quantity)),
    refund_total: refunds.length ? toMoney(sum(refunds.map((r) => r.amount))) : null,
    created_at: ret.created_at,
    updated_at: ret.updated_at,
  }
}

function pay(refund: MockRefund, approvedBy: string | null) {
  refund.status = 'paid'
  refund.approved_by = approvedBy
  refund.gateway_transaction_id =
    refund.method === 'original_payment' ? `GW-${refundIdTail(refund.refund_id)}` : null
  state.ledger.push({
    entry_id: state.next.entryId++,
    refund_id: refund.refund_id,
    entry_type: 'refund',
    method: refund.method,
    gateway_transaction_id: refund.gateway_transaction_id,
    amount: refund.amount,
    created_at: now(),
  })
}

// ---- Backend --------------------------------------------------------------------------

export const mockBackend: ReturnRightBackend = {
  async login({ username, password }) {
    await delay()
    const user = DEMO_STAFF.find((u) => u.username === username.trim().toLowerCase())
    if (!user || password !== DEMO_PASSWORD) {
      fail(401, 'invalid_credentials', 'Username or password is incorrect.')
    }
    return {
      access_token: `mock.${user!.role}`,
      token_type: 'bearer',
      expires_in: 28_800,
      role: user!.role,
    }
  },

  async lookupOrder({ order_number, email }) {
    await delay()
    const order = ORDERS.find((o) => o.order_number === order_number.trim().toUpperCase())
    const owner = order && customerOf(order.customer_id)
    if (!order || owner!.email !== email.trim().toLowerCase()) {
      fail(404, 'order_not_found', "We couldn't find an order with that number and email.")
    }
    const today = new Date()
    const items: ItemEligibilityResponse[] = order!.items.map((item) => {
      const open = state.returns.find(
        (r) =>
          r.order_number === order!.order_number &&
          r.status !== 'rejected' &&
          r.items.some((i) => i.order_item_id === item.order_item_id),
      )
      const rule = checkEligibility(item.category, order!.delivered_on, today)
      return {
        order_item_id: item.order_item_id,
        product_name: item.product_name,
        category: item.category,
        unit_price: toMoney(item.unit_price),
        quantity: item.quantity,
        eligible: rule.eligible && !open,
        reason: open ? `Already being returned in ${open.return_code}.` : rule.reason,
        window_ends_on: rule.windowEndsOn,
      }
    })
    return { order_number: order!.order_number, delivered_on: order!.delivered_on, items }
  },

  async createReturn(body) {
    await delay(500, 900)
    const lookup = await mockBackend.lookupOrder({
      order_number: body.order_number,
      email: body.email,
    })
    const order = ORDERS.find((o) => o.order_number === lookup.order_number)!
    const items = body.items.map((req) => {
      const line = lookup.items.find((i) => i.order_item_id === req.order_item_id)
      if (!line) return fail(422, 'unknown_item', 'An item is not part of this order.')
      if (!line.eligible)
        return fail(422, 'item_not_eligible', `${line.product_name}: ${line.reason}`)
      if (req.quantity > line.quantity) {
        return fail(
          422,
          'quantity_too_high',
          `You ordered ${line.quantity} of ${line.product_name}.`,
        )
      }
      return {
        return_item_id: state.next.returnItemId++,
        order_item_id: line.order_item_id,
        product_name: line.product_name,
        category: line.category,
        unit_price: Number(line.unit_price),
        quantity: req.quantity,
        grade: null,
        decision: null,
        refund_amount: null,
        notes: null,
      }
    })
    const at = now()
    const ret: MockReturn = {
      return_code: `RET-${state.next.returnNo++}`,
      order_number: order.order_number,
      customer_id: order.customer_id,
      status: 'requested',
      // The mock keeps one reason per return; the UI sends the same reason on every item.
      reason: body.items[0].reason,
      reason_details: body.items[0].reason_details ?? null,
      refund_method: body.refund_method,
      items,
      timeline: [{ status: 'requested', at, note: 'Return requested by the customer' }],
      created_at: at,
      updated_at: at,
    }
    transition(ret, 'approved', 'All items eligible; label issued')
    state.returns.push(ret)
    save()
    return toDetail(ret)
  },

  async uploadReturnPhoto(returnCode, email, returnItemId, photo) {
    await delay(400, 800)
    const ret = findReturn(returnCode)
    requireProof(ret, email)
    if (!ret.items.some((i) => i.return_item_id === returnItemId)) {
      fail(404, 'return_item_not_found', 'That item is not part of this return.')
    }
    photos.set(returnItemId, URL.createObjectURL(photo))
  },

  async getReturn(returnCode, { email }) {
    await delay()
    const ret = findReturn(returnCode)
    requireProof(ret, email)
    return toDetail(ret)
  },

  async getLabel(returnCode, { email }) {
    await delay()
    const ret = findReturn(returnCode)
    requireProof(ret, email)
    if (ret.status === 'requested' || ret.status === 'rejected') {
      fail(409, 'label_unavailable', 'A label is available once the return is approved.')
    }
    return {
      return_code: ret.return_code,
      qr_svg: mockQrSvg(ret.return_code),
      ship_to: WAREHOUSE_ADDRESS,
    }
  },

  async markShipped(returnCode, { email }) {
    await delay()
    const ret = findReturn(returnCode)
    requireProof(ret, email)
    if (ret.status !== 'approved') {
      fail(409, 'invalid_transition', 'This return has already been marked as shipped.')
    }
    transition(ret, 'in_transit', 'Customer marked the parcel as shipped')
    save()
    return toDetail(ret)
  },

  async listWarehouseQueue(status) {
    await delay()
    const items = state.returns
      .filter((r) => r.status === status)
      .sort((a, b) => a.updated_at.localeCompare(b.updated_at))
      .map(toSummary)
    return { items, total: items.length, page: 1, size: items.length }
  },

  async getReturnForStaff(returnCode) {
    await delay()
    return toDetail(findReturn(returnCode))
  },

  async markReceived(returnCode) {
    await delay()
    const ret = findReturn(returnCode)
    if (ret.status !== 'in_transit') {
      fail(
        409,
        'invalid_transition',
        `Only returns in transit can be received (this one is ${ret.status.replace('_', ' ')}).`,
      )
    }
    transition(ret, 'received', 'Parcel received at the warehouse')
    save()
    return toDetail(ret)
  },

  async inspectReturn(returnCode, { items: inspections }) {
    await delay(500, 900)
    const ret = findReturn(returnCode)
    if (ret.status !== 'received') {
      fail(409, 'invalid_transition', 'Only received returns can be inspected.')
    }
    if (inspections.length !== ret.items.length) {
      fail(422, 'incomplete_inspection', 'Grade and decide every item before submitting.')
    }
    for (const input of inspections) {
      const item = ret.items.find((i) => i.return_item_id === input.return_item_id)
      if (!item) return fail(422, 'unknown_item', 'An item is not part of this return.')
      item.grade = input.grade
      item.decision = input.decision
      item.notes = input.notes ?? null
      item.refund_amount = refundFor(item.unit_price, item.quantity, input.grade, input.decision)
    }
    const total = sum(ret.items.map((i) => i.refund_amount ?? 0))
    const accepted = ret.items.filter((i) => i.decision === 'accept')
    if (accepted.length === 0) {
      transition(ret, 'inspected', 'All items rejected at inspection')
      transition(ret, 'rejected', 'Return rejected after inspection')
    } else {
      transition(ret, 'inspected', `${accepted.length} of ${ret.items.length} items accepted`)
      const approval = needsApproval(total)
      for (const item of ret.items) {
        // One refund per return item: the API enforces this with a unique constraint.
        if (
          !item.refund_amount ||
          state.refunds.some((r) => r.return_item_id === item.return_item_id)
        )
          continue
        const refund: MockRefund = {
          refund_id: state.next.refundId++,
          return_code: ret.return_code,
          return_item_id: item.return_item_id,
          amount: item.refund_amount,
          method: ret.refund_method,
          status: 'pending_approval',
          gateway_transaction_id: null,
          approved_by: null,
          created_at: now(),
        }
        state.refunds.push(refund)
        if (!approval) pay(refund, null)
      }
      if (!approval) transition(ret, 'refunded', 'Refund paid')
    }
    save()
    return {
      return_code: ret.return_code,
      status: ret.status,
      items: toDetail(ret).items,
      refund_total: toMoney(total),
      needs_finance_approval: accepted.length > 0 && needsApproval(total),
    }
  },

  async listPendingApprovals() {
    await delay()
    const codes = [
      ...new Set(
        state.refunds.filter((r) => r.status === 'pending_approval').map((r) => r.return_code),
      ),
    ]
    return codes.map((code) => {
      const refunds = state.refunds.filter(
        (r) => r.return_code === code && r.status === 'pending_approval',
      )
      return {
        return_code: code,
        customer_flagged: isFlagged(findReturn(code).customer_id),
        refund_total: toMoney(sum(refunds.map((r) => r.amount))),
        refunds: refunds.map((r) => ({ ...r, amount: toMoney(r.amount) })),
      }
    })
  },

  async decideApproval(returnCode, { approve, comment }) {
    await delay(600, 1000)
    const ret = findReturn(returnCode)
    const pending = state.refunds.filter(
      (r) => r.return_code === ret.return_code && r.status === 'pending_approval',
    )
    if (pending.length === 0) {
      fail(409, 'already_decided', 'This refund has already been decided. Nothing was paid twice.')
    }
    if (approve) {
      pending.forEach((r) => pay(r, 'finance'))
      transition(
        ret,
        'refunded',
        comment ? `Approved by finance: ${comment}` : 'Approved by finance; refund paid',
      )
    } else {
      pending.forEach((r) => {
        r.status = 'rejected'
        r.approved_by = 'finance'
      })
      transition(
        ret,
        'rejected',
        comment ? `Rejected by finance: ${comment}` : 'Rejected by finance',
      )
    }
    save()
    const refunds = state.refunds.filter((r) => r.return_code === ret.return_code)
    return {
      return_code: ret.return_code,
      customer_flagged: isFlagged(ret.customer_id),
      refund_total: toMoney(sum(refunds.map((r) => r.amount))),
      refunds: refunds.map((r) => ({ ...r, amount: toMoney(r.amount) })),
    }
  },

  async listLedger() {
    await delay()
    const items = [...state.ledger]
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map((e) => ({ ...e, amount: toMoney(e.amount) }))
    return { items, total: items.length, page: 1, size: items.length }
  },

  async getDashboard(): Promise<DashboardResponse> {
    await delay()
    const live = (category: string) =>
      sum(state.returns.flatMap((r) => r.items.filter((i) => i.category === category).map(() => 1)))
    const return_rate_by_category = Object.entries(CATEGORY_ORDERS).map(([category, base]) => {
      const returns = base.returns + live(category)
      return { category, orders: base.orders, returns, return_rate: returns / base.orders }
    })
    const reasonCounts = { ...REASON_BASELINE }
    state.returns.forEach((r) => (reasonCounts[r.reason] += 1))
    const top_reasons = (Object.entries(reasonCounts) as [ReturnReason, number][])
      .map(([reason, count]) => ({ reason, count }))
      .sort((a, b) => b.count - a.count)
    const closed = state.returns.filter((r) => r.status === 'refunded' || r.status === 'rejected')
    const cycleHours = closed.map(
      (r) => (new Date(r.updated_at).getTime() - new Date(r.created_at).getTime()) / 3_600_000,
    )
    const flagged_customers = CUSTOMERS.filter((c) => isFlagged(c.customer_id))
      .map((c) => ({
        customer_id: c.customer_id,
        name: c.name,
        returns_last_30_days: returnsInLast30Days(c.customer_id),
      }))
      .sort((a, b) => b.returns_last_30_days - a.returns_last_30_days)
    return {
      return_rate_by_category,
      top_reasons,
      average_cycle_time_hours: cycleHours.length ? sum(cycleHours) / cycleHours.length : null,
      flagged_customers,
      generated_at: now(),
    }
  },
}
