import type { ReturnDetailResponse } from '../../api/types'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { formatDateTime } from '../../lib/format'
import { REASON_LABEL, REFUND_METHOD_LABEL } from '../../lib/labels'
import { StatusTimeline } from '../returns/components/StatusTimeline'

/** Side column shared by the warehouse and finance detail screens: facts, photo, audit trail. */
export function ReturnFacts({ detail }: { detail: ReturnDetailResponse }) {
  return (
    <div className="stack">
      <Card title="Return details">
        <dl className="facts">
          <div>
            <dt>Customer</dt>
            <dd>
              {detail.customer_name ?? '—'}{' '}
              {detail.customer_flagged && <Badge tone="warning">Flagged</Badge>}
            </dd>
          </div>
          <div>
            <dt>Order</dt>
            <dd className="mono">{detail.order_number ?? '—'}</dd>
          </div>
          <div>
            <dt>Reason</dt>
            <dd>
              {REASON_LABEL[detail.reason]}
              {detail.reason_details && <p className="muted">“{detail.reason_details}”</p>}
            </dd>
          </div>
          <div>
            <dt>Refund to</dt>
            <dd>{REFUND_METHOD_LABEL[detail.refund_method]}</dd>
          </div>
          <div>
            <dt>Requested</dt>
            <dd>{formatDateTime(detail.created_at)}</dd>
          </div>
        </dl>
      </Card>

      <Card title="Customer photo">
        {detail.photo_url ? (
          <img
            src={detail.photo_url}
            alt={`Customer photo for ${detail.return_code}`}
            className="photo"
          />
        ) : (
          <p className="muted">
            Photo is stored with the return; the preview appears once the API serves it.
          </p>
        )}
      </Card>

      <Card title="Audit trail" description="Every status change, oldest first.">
        <StatusTimeline status={detail.status} timeline={detail.timeline} />
      </Card>
    </div>
  )
}
