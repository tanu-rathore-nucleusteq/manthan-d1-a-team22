import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Badge, StatusBadge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { EmptyState } from '../../../components/ui/EmptyState'
import { ErrorState } from '../../../components/ui/ErrorState'
import { TextField } from '../../../components/ui/Field'
import { Icon } from '../../../components/ui/Icon'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { Segmented } from '../../../components/ui/Segmented'
import { StatTile } from '../../../components/ui/StatTile'
import { formatRelative } from '../../../lib/format'
import { isReturnCode, RETURN_CODE_EXAMPLE } from '../../../lib/returnCode'
import { useWarehouseQueue } from '../api'

type QueueStatus = 'in_transit' | 'received'

export function WarehouseQueuePage() {
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<QueueStatus>('received')
  const inTransit = useWarehouseQueue('in_transit')
  const received = useWarehouseQueue('received')
  const queue = tab === 'received' ? received : inTransit

  // A USB scanner types the code and presses Enter, so this form handles both.
  const open = (e: FormEvent) => {
    e.preventDefault()
    const value = code.trim().toUpperCase()
    if (!isReturnCode(value))
      return setError(`Scan the label or type a code like ${RETURN_CODE_EXAMPLE}.`)
    navigate(`/warehouse/returns/${value}`)
  }

  return (
    <>
      <PageHeader
        title="Inspection queue"
        subtitle="Receive parcels, grade items and decide refunds."
      />

      <div className="stats">
        <StatTile
          label="Waiting for inspection"
          icon="clipboardCheck"
          tone="warning"
          value={received.data ? String(received.data.total) : '…'}
          hint="Received, not yet graded"
        />
        <StatTile
          label="In transit"
          icon="truck"
          tone="info"
          value={inTransit.data ? String(inTransit.data.total) : '…'}
          hint="On the way to the warehouse"
        />
      </div>

      <Card className="scan-card">
        <span className="scan-card__icon">
          <Icon name="scan" size={24} />
        </span>
        <form
          className="scan-form"
          onSubmit={open}
          noValidate
          aria-label="Open a return by label code"
        >
          <TextField
            label="Scan or enter return code"
            className="scan-form__field"
            placeholder={RETURN_CODE_EXAMPLE}
            autoFocus
            autoComplete="off"
            value={code}
            error={error}
            onChange={(e) => {
              setCode(e.target.value)
              setError(null)
            }}
          />
          <Button type="submit">
            Open return
            <Icon name="arrowRight" size={16} />
          </Button>
        </form>
      </Card>

      <Card
        title="Parcels"
        actions={
          <Segmented<QueueStatus>
            legend="Queue"
            hideLegend
            size="sm"
            value={tab}
            onChange={setTab}
            options={[
              { value: 'received', label: `Received · ${received.data?.total ?? '…'}` },
              { value: 'in_transit', label: `In transit · ${inTransit.data?.total ?? '…'}` },
            ]}
          />
        }
        flush
      >
        {queue.isPending && <LoadingState lines={4} />}
        {queue.isError && <ErrorState error={queue.error} onRetry={() => queue.refetch()} />}
        {queue.data && queue.data.items.length === 0 && (
          <EmptyState
            icon={tab === 'received' ? 'checkCircle' : 'truck'}
            title={tab === 'received' ? 'Nothing waiting for inspection' : 'No parcels in transit'}
          >
            <p>New parcels appear here automatically.</p>
          </EmptyState>
        )}
        {queue.data && queue.data.items.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">
                {tab === 'received'
                  ? 'Received parcels waiting for inspection'
                  : 'Parcels in transit'}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Return</th>
                  <th scope="col">Order</th>
                  <th scope="col" className="num">
                    Items
                  </th>
                  <th scope="col">Status</th>
                  <th scope="col">Last update</th>
                  <th scope="col">
                    <span className="visually-hidden">Action</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {queue.data.items.map((r) => (
                  <tr key={r.return_code}>
                    <td>
                      <Link to={`/warehouse/returns/${r.return_code}`} className="mono">
                        {r.return_code}
                      </Link>
                    </td>
                    <td>
                      <span className="mono">{r.order_number}</span>{' '}
                      {r.customer_flagged && <Badge tone="warning">Flagged</Badge>}
                    </td>
                    <td className="num">{r.item_count}</td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="muted">{formatRelative(r.updated_at)}</td>
                    <td className="actions-cell">
                      <Link
                        to={`/warehouse/returns/${r.return_code}`}
                        className="btn btn--secondary btn--sm"
                      >
                        {r.status === 'received' ? 'Inspect' : 'Receive'}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
