import { Link } from 'react-router'

import { Badge } from '../../../components/ui/Badge'
import { Card } from '../../../components/ui/Card'
import { EmptyState } from '../../../components/ui/EmptyState'
import { ErrorState } from '../../../components/ui/ErrorState'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { StatTile } from '../../../components/ui/StatTile'
import { formatInr, formatRelative } from '../../../lib/format'
import { usePendingApprovals } from '../api'

export function ApprovalQueuePage() {
  const pending = usePendingApprovals()

  const rows = (pending.data ?? [])
    .map((p) => ({ ...p, since: p.refunds.map((r) => r.created_at).sort()[0] }))
    .sort((a, b) => a.since.localeCompare(b.since))
  const totalWaiting = rows.reduce((sum, r) => sum + Number(r.refund_total), 0)

  return (
    <>
      <PageHeader
        title="Refund approvals"
        subtitle="Returns totalling more than ₹10,000 wait here before the refund is paid."
      />

      <div className="stats">
        <StatTile
          label="Waiting for approval"
          icon="inbox"
          tone="warning"
          value={pending.data ? String(rows.length) : '…'}
        />
        <StatTile
          label="Amount waiting"
          icon="wallet"
          value={pending.data ? formatInr(totalWaiting) : '…'}
        />
        <StatTile
          label="Flagged customers"
          icon="flag"
          tone="danger"
          value={pending.data ? String(rows.filter((r) => r.customer_flagged).length) : '…'}
          hint="More than 3 returns in 30 days"
        />
      </div>

      <Card title="Queue" description="Oldest first." flush>
        {pending.isPending && <LoadingState lines={4} />}
        {pending.isError && <ErrorState error={pending.error} onRetry={() => pending.refetch()} />}
        {pending.data && rows.length === 0 && (
          <EmptyState title="All caught up" icon="checkCircle">
            <p>No refunds are waiting for approval.</p>
          </EmptyState>
        )}
        {rows.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">Refunds waiting for approval</caption>
              <thead>
                <tr>
                  <th scope="col">Return</th>
                  <th scope="col" className="num">
                    Refund total
                  </th>
                  <th scope="col" className="num">
                    Items
                  </th>
                  <th scope="col">Customer</th>
                  <th scope="col">Waiting</th>
                  <th scope="col">
                    <span className="visually-hidden">Action</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.return_code}>
                    <td>
                      <Link to={`/finance/returns/${r.return_code}`} className="mono">
                        {r.return_code}
                      </Link>
                    </td>
                    <td className="num">
                      <strong>{formatInr(r.refund_total)}</strong>
                    </td>
                    <td className="num">{r.refunds.length}</td>
                    <td>
                      {r.customer_flagged ? (
                        <Badge tone="warning">Flagged</Badge>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td className="muted">{formatRelative(r.since)}</td>
                    <td className="actions-cell">
                      <Link
                        to={`/finance/returns/${r.return_code}`}
                        className="btn btn--secondary btn--sm"
                      >
                        Review
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
