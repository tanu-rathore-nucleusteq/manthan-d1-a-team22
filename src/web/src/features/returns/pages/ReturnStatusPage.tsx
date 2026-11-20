import { Link, useParams } from 'react-router'

import { Alert } from '../../../components/ui/Alert'
import { Badge, StatusBadge } from '../../../components/ui/Badge'
import { Card } from '../../../components/ui/Card'
import { ErrorState } from '../../../components/ui/ErrorState'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { formatDate, formatInr } from '../../../lib/format'
import { REASON_LABEL, REFUND_METHOD_LABEL } from '../../../lib/labels'
import { useReturnDetail } from '../api'
import { ProofGate } from '../components/ProofGate'
import { StatusTimeline } from '../components/StatusTimeline'

export function ReturnStatusPage() {
  const { returnCode = '' } = useParams()
  return (
    <ProofGate returnCode={returnCode}>
      {(email) => <Status code={returnCode} email={email} />}
    </ProofGate>
  )
}

const MESSAGE = {
  requested: 'We are checking your return.',
  approved: 'Approved. Print your label and ship the parcel.',
  in_transit: 'Your parcel is on its way to our warehouse.',
  received: 'We have your parcel and will inspect it shortly.',
  inspected: 'Inspection is done; your refund is being processed.',
  refunded: 'Your refund has been paid.',
  rejected: 'This return was not accepted.',
} as const

function Status({ code, email }: { code: string; email: string }) {
  const detail = useReturnDetail(code, email)

  if (detail.isPending) return <LoadingState label="Loading your return" lines={5} />
  if (detail.isError) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />

  const r = detail.data
  const graded = r.items.some((i) => i.decision)

  return (
    <>
      <PageHeader
        title={`Return ${r.return_code}`}
        subtitle={`Requested on ${formatDate(r.created_at)}`}
        meta={<StatusBadge status={r.status} />}
        back={{ to: '/returns/track', label: 'Track another return' }}
      />

      <Alert
        tone={r.status === 'rejected' ? 'danger' : r.status === 'refunded' ? 'success' : 'info'}
      >
        {MESSAGE[r.status]}{' '}
        {r.status === 'approved' && <Link to={`/returns/${r.return_code}/label`}>View label</Link>}
      </Alert>

      <div className="detail-layout">
        <Card title="Progress">
          <StatusTimeline status={r.status} timeline={r.timeline} />
        </Card>

        <div className="stack">
          <Card title="Items" flush>
            <ul className="line-items">
              {r.items.map((i) => (
                <li key={i.return_item_id}>
                  <div>
                    <span className="line-items__name">{i.product_name}</span>
                    <span className="muted"> × {i.quantity}</span>
                    {i.decision && (
                      <div className="line-items__meta">
                        <Badge tone={i.decision === 'accept' ? 'success' : 'danger'}>
                          {i.decision === 'accept' ? 'Accepted' : 'Rejected'}
                        </Badge>
                        {i.grade && <span className="muted">Grade {i.grade}</span>}
                      </div>
                    )}
                  </div>
                  {graded && (
                    <span className="line-items__amount">{formatInr(i.refund_amount)}</span>
                  )}
                </li>
              ))}
            </ul>
            {graded && (
              <div className="summary-total summary-total--padded">
                <span>Refund total</span>
                <strong>{formatInr(r.refund_total)}</strong>
              </div>
            )}
          </Card>

          <Card title="Details">
            <dl className="facts">
              <div>
                <dt>Reason</dt>
                <dd>{[...new Set(r.items.map((i) => REASON_LABEL[i.reason]))].join(', ')}</dd>
              </div>
              <div>
                <dt>Refund to</dt>
                <dd>{REFUND_METHOD_LABEL[r.refund_method]}</dd>
              </div>
            </dl>
          </Card>
        </div>
      </div>
    </>
  )
}
