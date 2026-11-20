import { apiAssetUrl } from '../../api/client'
import type { ReturnDetailResponse } from '../../api/types'
import { Card } from '../../components/ui/Card'
import { formatDateTime } from '../../lib/format'
import { REASON_LABEL, REFUND_METHOD_LABEL } from '../../lib/labels'
import { StatusTimeline } from '../returns/components/StatusTimeline'

/** Side column shared by the warehouse and finance detail screens: facts, photos, audit trail. */
export function ReturnFacts({ detail }: { detail: ReturnDetailResponse }) {
  const photos = detail.items.flatMap((item) =>
    (item.photo_urls ?? []).map((url) => ({ url, item: item.product_name })),
  )

  return (
    <div className="stack">
      <Card title="Return details">
        <dl className="facts">
          <div>
            <dt>Refund to</dt>
            <dd>{REFUND_METHOD_LABEL[detail.refund_method]}</dd>
          </div>
          <div>
            <dt>Requested</dt>
            <dd>{formatDateTime(detail.created_at)}</dd>
          </div>
          {detail.items.map((item) => (
            <div key={item.return_item_id}>
              <dt>Reason</dt>
              <dd>
                {REASON_LABEL[item.reason]}
                {detail.items.length > 1 && <span className="muted"> · {item.product_name}</span>}
                {item.reason_details && <p className="muted">“{item.reason_details}”</p>}
              </dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card title="Customer photos">
        {photos.length > 0 ? (
          photos.map((p) => (
            <img
              key={p.url}
              src={apiAssetUrl(p.url)}
              alt={`Customer photo of ${p.item}`}
              className="photo"
            />
          ))
        ) : (
          <p className="muted">The customer didn't add a photo.</p>
        )}
      </Card>

      <Card title="Audit trail" description="Every status change, oldest first.">
        <StatusTimeline status={detail.status} timeline={detail.timeline} />
      </Card>
    </div>
  )
}
