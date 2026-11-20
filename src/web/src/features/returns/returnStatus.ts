/** Return lifecycle shown on the customer timeline. Order matches the API state machine. */
export const RETURN_STEPS = [
  'Requested',
  'Approved',
  'In transit',
  'Received',
  'Inspected',
] as const

/** Final states: a return ends in exactly one of these. */
export const FINAL_STATUSES = ['Refunded', 'Rejected'] as const

export type ReturnStatus = (typeof RETURN_STEPS)[number] | (typeof FINAL_STATUSES)[number]
