import type { Money } from '../api/types'

const inrWhole = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})
const inrPaise = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})
const date = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
const dateTime = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
})
const percent = new Intl.NumberFormat('en-IN', { style: 'percent', maximumFractionDigits: 1 })
const relative = new Intl.RelativeTimeFormat('en-IN', { numeric: 'auto' })

/** Formats an API Money string ("1299.00") or a number as INR: ₹1,299 or ₹1,099.50, never ₹1,099.5. */
export function formatInr(amount: Money | number | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') return '—'
  const value = Number(amount)
  return Number.isInteger(value) ? inrWhole.format(value) : inrPaise.format(value)
}

export const formatDate = (iso: string | null | undefined): string =>
  iso ? date.format(new Date(iso)) : '—'

export const formatDateTime = (iso: string): string => dateTime.format(new Date(iso))

export const formatPercent = (ratio: number): string => percent.format(ratio)

export const formatCount = (n: number): string => n.toLocaleString('en-IN')

export function formatRelative(iso: string): string {
  const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60_000)
  if (Math.abs(minutes) < 60) return relative.format(minutes, 'minute')
  const hours = Math.round(minutes / 60)
  if (Math.abs(hours) < 48) return relative.format(hours, 'hour')
  return relative.format(Math.round(hours / 24), 'day')
}

export function formatHours(hours: number | null): string {
  if (hours === null) return '—'
  return hours < 48 ? `${hours.toFixed(1)} h` : `${(hours / 24).toFixed(1)} days`
}
