const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
})

const date = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

export const formatInr = (amount: number): string => inr.format(amount)

export const formatDate = (iso: string): string => date.format(new Date(iso))
