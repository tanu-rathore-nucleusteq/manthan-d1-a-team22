import type { ReactNode } from 'react'

import type { RefundStatus, ReturnStatus } from '../../api/types'
import {
  REFUND_STATUS_LABEL,
  REFUND_STATUS_TONE,
  STATUS_LABEL,
  STATUS_TONE,
  type Tone,
} from '../../lib/labels'

/** Colour always comes with a text label, never alone. */
export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`badge badge--${tone}`}>
      <span className="badge__dot" aria-hidden="true" />
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: ReturnStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>
}

export function RefundStatusBadge({ status }: { status: RefundStatus }) {
  return <Badge tone={REFUND_STATUS_TONE[status]}>{REFUND_STATUS_LABEL[status]}</Badge>
}
