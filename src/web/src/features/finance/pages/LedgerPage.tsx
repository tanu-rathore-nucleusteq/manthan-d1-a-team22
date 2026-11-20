import { useState } from 'react'

import type { LedgerEntryType } from '../../../api/types'
import { Badge } from '../../../components/ui/Badge'
import { Card } from '../../../components/ui/Card'
import { EmptyState } from '../../../components/ui/EmptyState'
import { ErrorState } from '../../../components/ui/ErrorState'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { Segmented } from '../../../components/ui/Segmented'
import { StatTile } from '../../../components/ui/StatTile'
import { formatDateTime, formatInr } from '../../../lib/format'
import { LEDGER_TYPE_LABEL } from '../../../lib/labels'
import { useLedger } from '../api'

type Filter = 'all' | LedgerEntryType

export function LedgerPage() {
  const ledger = useLedger()
  const [filter, setFilter] = useState<Filter>('all')

  const entries = ledger.data?.items ?? []
  const shown = filter === 'all' ? entries : entries.filter((e) => e.entry_type === filter)
  const total = (type?: LedgerEntryType) =>
    entries
      .filter((e) => !type || e.entry_type === type)
      .reduce((sum, e) => sum + Number(e.amount), 0)

  return (
    <>
      <PageHeader
        title="Refund ledger"
        subtitle="One row per payment. A refund never appears twice."
      />

      <div className="stats">
        <StatTile
          label="Total refunded"
          icon="receipt"
          value={ledger.data ? formatInr(total()) : '…'}
        />
        <StatTile
          label="Through the gateway"
          icon="wallet"
          tone="info"
          value={ledger.data ? formatInr(total('gateway_refund')) : '…'}
        />
        <StatTile
          label="As store credit"
          icon="tag"
          tone="success"
          value={ledger.data ? formatInr(total('store_credit')) : '…'}
        />
        <StatTile
          label="Entries"
          icon="database"
          tone="neutral"
          value={ledger.data ? String(entries.length) : '…'}
        />
      </div>

      <Card
        title="Entries"
        description="Newest first."
        flush
        actions={
          <Segmented<Filter>
            legend="Filter by type"
            hideLegend
            size="sm"
            value={filter}
            onChange={setFilter}
            options={[
              { value: 'all', label: 'All' },
              { value: 'gateway_refund', label: 'Gateway' },
              { value: 'store_credit', label: 'Store credit' },
            ]}
          />
        }
      >
        {ledger.isPending && <LoadingState lines={5} />}
        {ledger.isError && <ErrorState error={ledger.error} onRetry={() => ledger.refetch()} />}
        {ledger.data && shown.length === 0 && (
          <EmptyState title="No ledger entries" icon="receipt" />
        )}
        {shown.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <caption className="visually-hidden">Ledger entries</caption>
              <thead>
                <tr>
                  <th scope="col">Entry</th>
                  <th scope="col">Refund</th>
                  <th scope="col">Type</th>
                  <th scope="col">Date</th>
                  <th scope="col" className="num">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody>
                {shown.map((e) => (
                  <tr key={e.entry_id}>
                    <td className="mono">#{e.entry_id}</td>
                    <td className="mono">#{e.refund_id}</td>
                    <td>
                      <Badge tone={e.entry_type === 'gateway_refund' ? 'info' : 'neutral'}>
                        {LEDGER_TYPE_LABEL[e.entry_type]}
                      </Badge>
                    </td>
                    <td className="muted">{formatDateTime(e.created_at)}</td>
                    <td className="num">{formatInr(e.amount)}</td>
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
