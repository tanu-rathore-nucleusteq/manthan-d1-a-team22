import { EmptyState } from '../../../components/ui/EmptyState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { formatInr } from '../../../lib/format'

export function ApprovalQueuePage() {
  return (
    <>
      <PageHeader
        title="Refund approvals"
        subtitle={`Returns totalling more than ${formatInr(10_000)} wait here for approval.`}
      />
      <EmptyState title="No refunds waiting for approval" />
    </>
  )
}
