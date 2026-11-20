import { Card } from '../../../components/ui/Card'
import { EmptyState } from '../../../components/ui/EmptyState'
import { ErrorState } from '../../../components/ui/ErrorState'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { StatTile } from '../../../components/ui/StatTile'
import { formatCount, formatHours, formatPercent, formatRelative } from '../../../lib/format'
import { REASON_LABEL } from '../../../lib/labels'
import { useDashboard } from '../api'
import { HBarChart } from '../components/HBarChart'

export function ManagerDashboardPage() {
  const dashboard = useDashboard()

  if (dashboard.isPending) {
    return (
      <>
        <PageHeader title="Returns dashboard" />
        <LoadingState label="Loading dashboard" lines={8} />
      </>
    )
  }
  if (dashboard.isError) {
    return (
      <>
        <PageHeader title="Returns dashboard" />
        <ErrorState error={dashboard.error} onRetry={() => dashboard.refetch()} />
      </>
    )
  }

  const d = dashboard.data
  const orders = d.return_rate_by_category.reduce((sum, c) => sum + c.orders, 0)
  const returns = d.return_rate_by_category.reduce((sum, c) => sum + c.returns, 0)
  const byRate = [...d.return_rate_by_category].sort((a, b) => b.return_rate - a.return_rate)
  const reasonTotal = d.top_reasons.reduce((sum, r) => sum + r.count, 0)

  return (
    <>
      <PageHeader
        title="Returns dashboard"
        subtitle={`Updated ${formatRelative(d.generated_at)} · refreshes every minute`}
      />

      <div className="stats">
        <StatTile
          label="Return rate"
          value={orders ? formatPercent(returns / orders) : '—'}
          hint={`${formatCount(returns)} returns of ${formatCount(orders)} orders`}
        />
        <StatTile
          label="Average cycle time"
          value={formatHours(d.average_cycle_time_hours)}
          hint="Request to refund or rejection"
        />
        <StatTile
          label="Top reason"
          value={d.top_reasons[0] ? REASON_LABEL[d.top_reasons[0].reason] : '—'}
          hint={d.top_reasons[0] ? `${d.top_reasons[0].count} returns` : undefined}
        />
        <StatTile
          label="Flagged customers"
          value={String(d.flagged_customers.length)}
          hint="More than 3 returns in 30 days"
        />
      </div>

      <div className="grid-2 grid-2--top">
        <Card title="Return rate by category" description="Returns as a share of orders.">
          <HBarChart
            measure="Return rate"
            data={byRate.map((c) => ({
              label: c.category,
              value: c.return_rate,
              display: formatPercent(c.return_rate),
              detail: `${formatCount(c.returns)} returns of ${formatCount(c.orders)} orders`,
            }))}
          />
        </Card>

        <Card title="Top return reasons" description="Number of returns per reason.">
          <HBarChart
            measure="Returns"
            data={d.top_reasons.map((r) => ({
              label: REASON_LABEL[r.reason],
              value: r.count,
              display: String(r.count),
              detail: reasonTotal
                ? `${formatPercent(r.count / reasonTotal)} of all returns`
                : undefined,
            }))}
          />
        </Card>
      </div>

      <Card
        title="Flagged customers"
        description="Flagged customers can still return items; review their returns closely."
        flush
      >
        {d.flagged_customers.length === 0 ? (
          <EmptyState title="No flagged customers" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">
                Customers with more than 3 returns in 30 days
              </caption>
              <thead>
                <tr>
                  <th scope="col">Customer</th>
                  <th scope="col">ID</th>
                  <th scope="col" className="num">
                    Returns in last 30 days
                  </th>
                </tr>
              </thead>
              <tbody>
                {d.flagged_customers.map((c) => (
                  <tr key={c.customer_id}>
                    <td>{c.name}</td>
                    <td className="mono">#{c.customer_id}</td>
                    <td className="num">
                      <strong>{c.returns_last_30_days}</strong>
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
