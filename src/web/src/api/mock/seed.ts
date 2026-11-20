/** Synthetic demo data only. Names and emails are invented; every email is @example.com. */
import type {
  Grade,
  ItemDecision,
  LedgerEntryType,
  RefundMethod,
  RefundStatus,
  ReturnReason,
  ReturnStatus,
  StatusEventResponse,
} from '../types'
import { needsApproval, refundFor } from './rules'

export interface MockCustomer {
  customer_id: number
  name: string
  email: string
}

export interface MockOrderItem {
  order_item_id: number
  product_name: string
  category: string
  unit_price: number
  quantity: number
}

export interface MockOrder {
  order_number: string
  customer_id: number
  delivered_on: string | null
  items: MockOrderItem[]
}

export interface MockReturnItem {
  return_item_id: number
  order_item_id: number
  product_name: string
  category: string
  unit_price: number
  quantity: number
  grade: Grade | null
  decision: ItemDecision | null
  refund_amount: number | null
  notes: string | null
}

export interface MockReturn {
  return_code: string
  order_number: string
  customer_id: number
  status: ReturnStatus
  reason: ReturnReason
  reason_details: string | null
  refund_method: RefundMethod
  items: MockReturnItem[]
  timeline: StatusEventResponse[]
  created_at: string
  updated_at: string
}

export interface MockRefund {
  refund_id: number
  return_code: string
  return_item_id: number
  amount: number
  method: RefundMethod
  status: RefundStatus
  gateway_transaction_id: string | null
  approved_by: string | null
  created_at: string
}

export interface MockLedgerEntry {
  entry_id: number
  refund_id: number
  entry_type: LedgerEntryType
  method: RefundMethod
  gateway_transaction_id: string | null
  amount: number
  created_at: string
}

export interface MockState {
  version: number
  returns: MockReturn[]
  refunds: MockRefund[]
  ledger: MockLedgerEntry[]
  next: { returnNo: number; returnItemId: number; refundId: number; entryId: number }
}

const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString()
const daysAgoDate = (d: number) => hoursAgo(d * 24).slice(0, 10)

export const CUSTOMERS: MockCustomer[] = [
  { customer_id: 1, name: 'Asha Verma', email: 'asha.verma@example.com' },
  { customer_id: 2, name: 'Rohan Mehta', email: 'rohan.mehta@example.com' },
  { customer_id: 3, name: 'Neha Iyer', email: 'neha.iyer@example.com' },
  { customer_id: 4, name: 'Kabir Singh', email: 'kabir.singh@example.com' },
  { customer_id: 11, name: 'Priya Nair', email: 'priya.nair@example.com' },
  { customer_id: 12, name: 'Arjun Rao', email: 'arjun.rao@example.com' },
  { customer_id: 13, name: 'Kavya Menon', email: 'kavya.menon@example.com' },
  { customer_id: 14, name: 'Vikram Shah', email: 'vikram.shah@example.com' },
  { customer_id: 15, name: 'Sneha Kulkarni', email: 'sneha.kulkarni@example.com' },
  { customer_id: 16, name: 'Rahul Gupta', email: 'rahul.gupta@example.com' },
  { customer_id: 17, name: 'Ananya Das', email: 'ananya.das@example.com' },
  { customer_id: 18, name: 'Imran Khan', email: 'imran.khan@example.com' },
  { customer_id: 19, name: 'Meera Joshi', email: 'meera.joshi@example.com' },
  { customer_id: 20, name: 'Dev Patel', email: 'dev.patel@example.com' },
]

/** Orders customers can look up. Dates are relative to today so the demo cases never expire. */
export const ORDERS: MockOrder[] = [
  {
    // Demo beat: electronics on day 11 is refused; the kurta is eligible; innerwear never is.
    order_number: 'RR-10021',
    customer_id: 1,
    delivered_on: daysAgoDate(11),
    items: [
      {
        order_item_id: 101,
        product_name: 'Wireless headphones',
        category: 'Electronics',
        unit_price: 3499,
        quantity: 1,
      },
      {
        order_item_id: 102,
        product_name: 'Cotton kurta',
        category: 'Apparel',
        unit_price: 1299,
        quantity: 2,
      },
      {
        order_item_id: 103,
        product_name: 'Cotton briefs (pack of 3)',
        category: 'Innerwear',
        unit_price: 599,
        quantity: 1,
      },
    ],
  },
  {
    // Demo beat: a high-value return goes to finance approval (> 10,000 INR).
    order_number: 'RR-10022',
    customer_id: 2,
    delivered_on: daysAgoDate(5),
    items: [
      {
        order_item_id: 201,
        product_name: '43-inch 4K smart TV',
        category: 'Electronics',
        unit_price: 28999,
        quantity: 1,
      },
      {
        order_item_id: 202,
        product_name: 'HDMI cable, 2 m',
        category: 'Electronics',
        unit_price: 499,
        quantity: 1,
      },
    ],
  },
  {
    order_number: 'RR-10023',
    customer_id: 3,
    delivered_on: daysAgoDate(40),
    items: [
      {
        order_item_id: 301,
        product_name: 'Cushion covers (set of 5)',
        category: 'Home & Kitchen',
        unit_price: 899,
        quantity: 1,
      },
    ],
  },
  {
    order_number: 'RR-10024',
    customer_id: 4,
    delivered_on: daysAgoDate(2),
    items: [
      {
        order_item_id: 401,
        product_name: 'Running shoes',
        category: 'Apparel',
        unit_price: 4599,
        quantity: 1,
      },
      {
        order_item_id: 402,
        product_name: 'Steel water bottle',
        category: 'Home & Kitchen',
        unit_price: 699,
        quantity: 2,
      },
      {
        order_item_id: 403,
        product_name: 'Vitamin C face serum',
        category: 'Beauty',
        unit_price: 799,
        quantity: 1,
      },
      {
        order_item_id: 404,
        product_name: 'Alphonso mangoes, 1 dozen',
        category: 'Perishables',
        unit_price: 1199,
        quantity: 1,
      },
    ],
  },
]

export const DEMO_ORDERS = ORDERS.map((o) => ({
  orderNumber: o.order_number,
  email: CUSTOMERS.find((c) => c.customer_id === o.customer_id)!.email,
  note: {
    'RR-10021': 'Electronics on day 11 (refused), kurta eligible, innerwear never',
    'RR-10022': 'High-value TV: needs finance approval',
    'RR-10023': 'Delivered 40 days ago: window closed',
    'RR-10024': 'Mixed basket, perishables never returnable',
  }[o.order_number]!,
}))

export const DEMO_STAFF = [
  { username: 'warehouse', role: 'warehouse_agent', label: 'Warehouse agent' },
  { username: 'finance', role: 'finance_reviewer', label: 'Finance reviewer' },
  { username: 'manager', role: 'operations_manager', label: 'Operations manager' },
] as const
export const DEMO_PASSWORD = 'demo1234'

/** Baseline order volumes per category for the dashboard (the API computes these from orders). */
export const CATEGORY_ORDERS: Record<string, { orders: number; returns: number }> = {
  Electronics: { orders: 412, returns: 41 },
  Apparel: { orders: 638, returns: 96 },
  'Home & Kitchen': { orders: 377, returns: 27 },
  Beauty: { orders: 254, returns: 9 },
  Innerwear: { orders: 183, returns: 0 },
  Perishables: { orders: 136, returns: 0 },
}

export const REASON_BASELINE: Record<ReturnReason, number> = {
  size: 58,
  damaged: 39,
  not_as_described: 31,
  wrong_item: 22,
  changed_mind: 17,
  quality: 9,
  other: 6,
}

interface SeedItem {
  name: string
  category: string
  price: number
  qty?: number
  grade?: Grade
  decision?: ItemDecision
}

interface SeedReturn {
  code: string
  customer: number
  status: ReturnStatus
  ageHours: number
  reason: ReturnReason
  details?: string
  method: RefundMethod
  items: SeedItem[]
}

const SEED_RETURNS: SeedReturn[] = [
  {
    code: 'RET-24051',
    customer: 11,
    status: 'in_transit',
    ageHours: 70,
    reason: 'damaged',
    details: 'Scroll wheel stopped working after two days.',
    method: 'original_payment',
    items: [{ name: 'Wireless mouse', category: 'Electronics', price: 1299 }],
  },
  {
    code: 'RET-24052',
    customer: 12,
    status: 'in_transit',
    ageHours: 50,
    reason: 'size',
    method: 'store_credit',
    items: [
      { name: 'Denim jacket', category: 'Apparel', price: 2799 },
      { name: 'Leather belt', category: 'Apparel', price: 899 },
    ],
  },
  {
    code: 'RET-24053',
    customer: 13,
    status: 'in_transit',
    ageHours: 26,
    reason: 'not_as_described',
    details: 'Coating is grey, listing showed black.',
    method: 'original_payment',
    items: [{ name: 'Non-stick pan set', category: 'Home & Kitchen', price: 3450 }],
  },
  {
    code: 'RET-24054',
    customer: 14,
    status: 'received',
    ageHours: 96,
    reason: 'damaged',
    details: 'Screen cracked on arrival.',
    method: 'original_payment',
    items: [{ name: 'Smartwatch with GPS', category: 'Electronics', price: 12999 }],
  },
  {
    code: 'RET-24055',
    customer: 15,
    status: 'received',
    ageHours: 75,
    reason: 'wrong_item',
    method: 'store_credit',
    items: [{ name: 'Ceramic dinner set', category: 'Home & Kitchen', price: 2199 }],
  },
  {
    code: 'RET-24056',
    customer: 16,
    status: 'inspected',
    ageHours: 140,
    reason: 'damaged',
    method: 'original_payment',
    items: [
      {
        name: 'Noise-cancelling headphones',
        category: 'Electronics',
        price: 14999,
        grade: 'A',
        decision: 'accept',
      },
    ],
  },
  {
    code: 'RET-24057',
    customer: 17,
    status: 'inspected',
    ageHours: 120,
    reason: 'not_as_described',
    details: 'Colour differs from photos.',
    method: 'original_payment',
    items: [
      { name: 'Silk saree', category: 'Apparel', price: 9499, grade: 'A', decision: 'accept' },
      {
        name: 'Embroidered dupatta',
        category: 'Apparel',
        price: 2499,
        grade: 'C',
        decision: 'accept',
      },
    ],
  },
  {
    code: 'RET-24058',
    customer: 17,
    status: 'refunded',
    ageHours: 290,
    reason: 'size',
    method: 'store_credit',
    items: [
      { name: 'Printed kurta', category: 'Apparel', price: 1299, grade: 'A', decision: 'accept' },
    ],
  },
  {
    code: 'RET-24059',
    customer: 17,
    status: 'refunded',
    ageHours: 480,
    reason: 'size',
    method: 'original_payment',
    items: [
      { name: 'Palazzo pants', category: 'Apparel', price: 999, grade: 'B', decision: 'accept' },
    ],
  },
  {
    code: 'RET-24060',
    customer: 17,
    status: 'approved',
    ageHours: 190,
    reason: 'changed_mind',
    method: 'store_credit',
    items: [{ name: 'Cotton top', category: 'Apparel', price: 799 }],
  },
  {
    code: 'RET-24061',
    customer: 18,
    status: 'refunded',
    ageHours: 216,
    reason: 'damaged',
    method: 'original_payment',
    items: [
      {
        name: 'Bluetooth speaker',
        category: 'Electronics',
        price: 2499,
        grade: 'B',
        decision: 'accept',
      },
    ],
  },
  {
    code: 'RET-24062',
    customer: 19,
    status: 'rejected',
    ageHours: 168,
    reason: 'changed_mind',
    method: 'original_payment',
    items: [
      {
        name: 'Vitamin C face serum',
        category: 'Beauty',
        price: 799,
        grade: 'C',
        decision: 'reject',
      },
    ],
  },
  {
    code: 'RET-24063',
    customer: 20,
    status: 'refunded',
    ageHours: 360,
    reason: 'damaged',
    details: 'Basket handle broke.',
    method: 'original_payment',
    items: [
      {
        name: 'Air fryer, 4 L',
        category: 'Home & Kitchen',
        price: 6499,
        grade: 'C',
        decision: 'accept',
      },
    ],
  },
]

const FLOW: ReturnStatus[] = ['requested', 'approved', 'in_transit', 'received', 'inspected']
const NOTES: Partial<Record<ReturnStatus, string>> = {
  approved: 'All items eligible; label issued',
  in_transit: 'Customer marked the parcel as shipped',
  received: 'Parcel received at the warehouse',
  inspected: 'Items graded',
  refunded: 'Refund paid',
  rejected: 'Return rejected after inspection',
}

export function buildTimeline(status: ReturnStatus, ageHours: number): StatusEventResponse[] {
  const stops =
    status === 'refunded' || status === 'rejected'
      ? [...FLOW, status]
      : FLOW.slice(0, FLOW.indexOf(status) + 1)
  const step = ageHours / Math.max(stops.length, 1)
  return stops.map((s, i) => ({
    status: s,
    at: hoursAgo(ageHours - step * i - (i === 0 ? 0 : 0.2)),
    note: NOTES[s] ?? null,
  }))
}

export function createSeedState(): MockState {
  const state: MockState = {
    version: 1,
    returns: [],
    refunds: [],
    ledger: [],
    next: { returnNo: 24064, returnItemId: 9001, refundId: 5001, entryId: 7001 },
  }

  for (const seed of SEED_RETURNS) {
    const timeline = buildTimeline(seed.status, seed.ageHours)
    const inspected = ['inspected', 'refunded', 'rejected'].includes(seed.status)
    const items: MockReturnItem[] = seed.items.map((it, i) => {
      const qty = it.qty ?? 1
      const graded = inspected && it.grade && it.decision
      return {
        return_item_id: state.next.returnItemId++,
        order_item_id: 800 + i,
        product_name: it.name,
        category: it.category,
        unit_price: it.price,
        quantity: qty,
        grade: graded ? it.grade! : null,
        decision: graded ? it.decision! : null,
        refund_amount: graded ? refundFor(it.price, qty, it.grade!, it.decision!) : null,
        notes: null,
      }
    })
    const ret: MockReturn = {
      return_code: seed.code,
      order_number: `RR-${seed.code.slice(4)}`,
      customer_id: seed.customer,
      status: seed.status,
      reason: seed.reason,
      reason_details: seed.details ?? null,
      refund_method: seed.method,
      items,
      timeline,
      created_at: timeline[0].at,
      updated_at: timeline[timeline.length - 1].at,
    }
    state.returns.push(ret)

    if (!inspected) continue
    const total = items.reduce((sum, it) => sum + (it.refund_amount ?? 0), 0)
    const inspectedAt = timeline.find((e) => e.status === 'inspected')!.at
    for (const it of items) {
      if (!it.refund_amount) continue
      const pending = seed.status === 'inspected' && needsApproval(total)
      const refund: MockRefund = {
        refund_id: state.next.refundId++,
        return_code: seed.code,
        return_item_id: it.return_item_id,
        amount: it.refund_amount,
        method: seed.method,
        status: pending ? 'pending_approval' : 'paid',
        gateway_transaction_id:
          !pending && seed.method === 'original_payment'
            ? `GW-${refundIdTail(state.next.refundId)}`
            : null,
        approved_by: null,
        created_at: inspectedAt,
      }
      state.refunds.push(refund)
      if (refund.status === 'paid') {
        state.ledger.push({
          entry_id: state.next.entryId++,
          refund_id: refund.refund_id,
          entry_type: 'refund',
          method: refund.method,
          gateway_transaction_id: refund.gateway_transaction_id,
          amount: refund.amount,
          created_at: ret.updated_at,
        })
      }
    }
  }
  return state
}

export const refundIdTail = (n: number) => `${n}`.padStart(6, '0')
