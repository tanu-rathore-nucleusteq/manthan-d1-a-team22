import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { getErrorMessage } from '../../../api/errors'
import { useStaffReturn } from '../../../api/staffQueries'
import { useToast } from '../../../components/toast/toastContext'
import { Alert } from '../../../components/ui/Alert'
import { Badge, RefundStatusBadge, StatusBadge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog'
import { ErrorState } from '../../../components/ui/ErrorState'
import { TextAreaField } from '../../../components/ui/Field'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { formatInr } from '../../../lib/format'
import { REFUND_METHOD_LABEL } from '../../../lib/labels'
import { GradedItemsTable } from '../../staff/GradedItemsTable'
import { ReturnFacts } from '../../staff/ReturnFacts'
import { useDecideApproval, usePendingApprovals } from '../api'

export function ApprovalDetailPage() {
  const { returnCode = '' } = useParams()
  const code = returnCode.toUpperCase()
  const navigate = useNavigate()
  const toast = useToast()
  const detail = useStaffReturn(code)
  const pending = usePendingApprovals()
  const decide = useDecideApproval(code)
  const [dialog, setDialog] = useState<'approve' | 'reject' | null>(null)
  const [comment, setComment] = useState('')

  if (detail.isPending || pending.isPending)
    return <LoadingState label="Loading refund" lines={6} />
  if (detail.isError) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />
  if (pending.isError) return <ErrorState error={pending.error} onRetry={() => pending.refetch()} />

  const approval = pending.data.find((p) => p.return_code === code)
  const itemName = (id: number) =>
    detail.data.items.find((i) => i.return_item_id === id)?.product_name ?? `Item ${id}`

  const confirm = () => {
    const approve = dialog === 'approve'
    decide.mutate(
      { approve, comment: comment.trim() || null },
      {
        onSuccess: (result) => {
          const paid = result.status === 'refunded'
          toast({
            tone: !approve ? 'info' : paid ? 'success' : 'danger',
            title: !approve
              ? `Refund for ${code} rejected`
              : paid
                ? `Refund for ${code} approved and paid`
                : `Refund for ${code} approved; the payment didn't go through and needs a retry`,
          })
          navigate('/finance')
        },
        onError: () => setDialog(null),
      },
    )
  }

  return (
    <>
      <PageHeader
        title={code}
        subtitle={
          approval
            ? `Refund of ${formatInr(approval.refund_total)} waiting for approval`
            : 'No refund waiting for approval'
        }
        meta={<StatusBadge status={detail.data.status} />}
        back={{ to: '/finance', label: 'Refund approvals' }}
        actions={
          approval && (
            <>
              <Button
                variant="danger"
                onClick={() => setDialog('reject')}
                disabled={decide.isPending}
              >
                Reject
              </Button>
              <Button onClick={() => setDialog('approve')} disabled={decide.isPending}>
                Approve refund
              </Button>
            </>
          )
        }
      />

      {decide.isError && (
        <Alert tone="danger" title="Decision not saved">
          {getErrorMessage(decide.error)}
        </Alert>
      )}

      <div className="detail-layout detail-layout--wide">
        <div className="stack">
          {approval?.customer_flagged && (
            <Alert tone="warning" title="Flagged customer">
              This customer has made more than 3 returns in the last 30 days. The return can still
              be approved; check the photo and inspection notes first.
            </Alert>
          )}

          {approval ? (
            <Card title="Refunds to approve" flush>
              <div className="table-wrap">
                <table className="table">
                  <caption className="visually-hidden">Refunds waiting for approval</caption>
                  <thead>
                    <tr>
                      <th scope="col">Item</th>
                      <th scope="col">Method</th>
                      <th scope="col">Status</th>
                      <th scope="col" className="num">
                        Amount
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {approval.refunds.map((r) => (
                      <tr key={r.refund_id}>
                        <td>{itemName(r.return_item_id)}</td>
                        <td>{REFUND_METHOD_LABEL[r.method]}</td>
                        <td>
                          <RefundStatusBadge status={r.status} />
                        </td>
                        <td className="num">{formatInr(r.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th scope="row" colSpan={3}>
                        Total
                      </th>
                      <td className="num">
                        <strong>{formatInr(approval.refund_total)}</strong>
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </Card>
          ) : (
            <Alert tone="info" title="Nothing to approve">
              This return has no refund waiting for approval. It may already have been decided.
            </Alert>
          )}

          <Card title="Inspection" flush>
            <GradedItemsTable items={detail.data.items} total={detail.data.refund_total} />
          </Card>
        </div>

        <ReturnFacts detail={detail.data} />
      </div>

      <ConfirmDialog
        open={dialog !== null}
        title={dialog === 'approve' ? `Approve refund for ${code}?` : `Reject refund for ${code}?`}
        confirmLabel={dialog === 'approve' ? 'Approve and pay' : 'Reject refund'}
        tone={dialog === 'approve' ? 'primary' : 'danger'}
        busy={decide.isPending}
        confirmDisabled={dialog === 'reject' && !comment.trim()}
        onCancel={() => setDialog(null)}
        onConfirm={confirm}
      >
        <p>
          {dialog === 'approve'
            ? `${formatInr(approval?.refund_total)} will be paid through the payment gateway or as store credit. This happens once, even if you click twice.`
            : 'The customer will not be refunded and the return will be closed as rejected.'}
        </p>
        {approval?.customer_flagged && <Badge tone="warning">Flagged customer</Badge>}
        <TextAreaField
          label={dialog === 'reject' ? 'Reason for rejecting (required)' : 'Comment (optional)'}
          rows={3}
          maxLength={500}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
      </ConfirmDialog>
    </>
  )
}
