import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { ApiError, getErrorMessage } from '../../../api/errors'
import { useStaffReturn } from '../../../api/staffQueries'
import type {
  Grade,
  InspectionResultResponse,
  ItemDecision,
  ReturnDetailResponse,
} from '../../../api/types'
import { useToast } from '../../../components/toast/toastContext'
import { Alert } from '../../../components/ui/Alert'
import { StatusBadge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { ErrorState } from '../../../components/ui/ErrorState'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { Segmented } from '../../../components/ui/Segmented'
import { formatInr } from '../../../lib/format'
import { ReturnFacts } from '../../staff/ReturnFacts'
import { GradedItemsTable } from '../../staff/GradedItemsTable'
import { useInspectReturn, useMarkReceived } from '../api'

const GRADES: { value: Grade; label: string; hint: string }[] = [
  { value: 'A', label: 'A', hint: 'As new: full refund' },
  { value: 'B', label: 'B', hint: 'Minor wear: full refund' },
  { value: 'C', label: 'C', hint: 'Used or damaged: 50% refund' },
]
const DECISIONS: { value: ItemDecision; label: string }[] = [
  { value: 'accept', label: 'Accept' },
  { value: 'reject', label: 'Reject' },
]
const APPROVAL_THRESHOLD = 10_000

export function InspectionPage() {
  const { returnCode = '' } = useParams()
  const detail = useStaffReturn(returnCode)

  if (detail.isPending) return <LoadingState label="Loading return" lines={6} />
  if (detail.isError) {
    const notFound = detail.error instanceof ApiError && detail.error.status === 404
    return (
      <>
        <PageHeader
          title={returnCode.toUpperCase()}
          back={{ to: '/warehouse', label: 'Inspection queue' }}
        />
        <ErrorState
          title={notFound ? 'Return not found' : 'Could not load this return'}
          error={detail.error}
          onRetry={notFound ? undefined : () => detail.refetch()}
        />
      </>
    )
  }
  return <Inspection detail={detail.data} />
}

function Inspection({ detail }: { detail: ReturnDetailResponse }) {
  const code = detail.return_code
  const toast = useToast()
  const receive = useMarkReceived(code)
  const inspect = useInspectReturn(code)
  const [result, setResult] = useState<InspectionResultResponse | null>(null)

  return (
    <>
      <PageHeader
        title={code}
        subtitle={`${detail.customer_name ?? 'Customer'} · order ${detail.order_number ?? '—'}`}
        meta={<StatusBadge status={detail.status} />}
        back={{ to: '/warehouse', label: 'Inspection queue' }}
      />

      <div className="detail-layout detail-layout--wide">
        <div className="stack">
          {result && <ResultCard result={result} />}

          {!result && detail.status === 'in_transit' && (
            <Card title="Receive parcel">
              <p>
                Check the label matches this return, then mark the parcel as received to start
                inspection.
              </p>
              {receive.isError && (
                <Alert tone="danger" title="Couldn't mark as received">
                  {getErrorMessage(receive.error)}
                </Alert>
              )}
              <Button
                loading={receive.isPending}
                onClick={() =>
                  receive.mutate(undefined, {
                    onSuccess: () => toast({ tone: 'success', title: `${code} received` }),
                  })
                }
              >
                Mark as received
              </Button>
            </Card>
          )}

          {!result && detail.status === 'received' && (
            <InspectionForm
              detail={detail}
              submitting={inspect.isPending}
              error={inspect.isError ? getErrorMessage(inspect.error) : null}
              onSubmit={(items) =>
                inspect.mutate(
                  { items },
                  {
                    onSuccess: (res) => {
                      setResult(res)
                      toast({ tone: 'success', title: `${code} inspected` })
                    },
                  },
                )
              }
            />
          )}

          {!result && (detail.status === 'requested' || detail.status === 'approved') && (
            <Alert tone="info" title="Not shipped yet">
              The customer has not shipped this parcel. It will appear in the queue once it is in
              transit.
            </Alert>
          )}

          {!result && ['inspected', 'refunded', 'rejected'].includes(detail.status) && (
            <Card title="Inspection result" flush>
              <GradedItemsTable items={detail.items} total={detail.refund_total} />
            </Card>
          )}
        </div>

        <ReturnFacts detail={detail} />
      </div>
    </>
  )
}

interface ItemState {
  grade: Grade | null
  decision: ItemDecision | null
  notes: string
}

function InspectionForm({
  detail,
  submitting,
  error,
  onSubmit,
}: {
  detail: ReturnDetailResponse
  submitting: boolean
  error: string | null
  onSubmit: (
    items: { return_item_id: number; grade: Grade; decision: ItemDecision; notes: string | null }[],
  ) => void
}) {
  const [state, setState] = useState<Record<number, ItemState>>(() =>
    Object.fromEntries(
      detail.items.map((i) => [i.return_item_id, { grade: null, decision: null, notes: '' }]),
    ),
  )
  const [showErrors, setShowErrors] = useState(false)

  const update = (id: number, patch: Partial<ItemState>) =>
    setState((s) => ({ ...s, [id]: { ...s[id], ...patch } }))

  const preview = (id: number) => {
    const item = detail.items.find((i) => i.return_item_id === id)!
    const { grade, decision } = state[id]
    if (!grade || !decision || !item.unit_price) return null
    if (decision === 'reject') return 0
    return Number(item.unit_price) * item.quantity * (grade === 'C' ? 0.5 : 1)
  }

  const previews = detail.items.map((i) => preview(i.return_item_id))
  const complete = previews.every((p) => p !== null)
  const total = previews.reduce<number>((sum, p) => sum + (p ?? 0), 0)

  const submit = () => {
    setShowErrors(true)
    if (!complete) return
    onSubmit(
      detail.items.map((i) => ({
        return_item_id: i.return_item_id,
        grade: state[i.return_item_id].grade!,
        decision: state[i.return_item_id].decision!,
        notes: state[i.return_item_id].notes.trim() || null,
      })),
    )
  }

  return (
    <Card
      title="Grade and decide each item"
      description="Grade A and B refund in full, grade C refunds 50%. Rejected items are not refunded."
      actions={
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            setState((s) =>
              Object.fromEntries(
                Object.entries(s).map(([id, v]) => [id, { ...v, grade: 'A', decision: 'accept' }]),
              ),
            )
          }
        >
          Quick fill: all A, accept
        </Button>
      }
    >
      <ul className="inspect-list">
        {detail.items.map((item, index) => {
          const s = state[item.return_item_id]
          const missing = showErrors && (!s.grade || !s.decision)
          return (
            <li
              key={item.return_item_id}
              className={missing ? 'inspect-item inspect-item--error' : 'inspect-item'}
            >
              <div className="inspect-item__head">
                <div>
                  <span className="inspect-item__name">{item.product_name}</span>
                  <span className="muted">
                    {' '}
                    × {item.quantity}
                    {item.unit_price && ` · ${formatInr(item.unit_price)} each`}
                  </span>
                </div>
                <span className="inspect-item__refund">
                  {previews[index] === null ? '—' : formatInr(previews[index])}
                </span>
              </div>
              <div className="inspect-item__controls">
                <Segmented
                  legend={`Grade for ${item.product_name}`}
                  options={GRADES}
                  value={s.grade}
                  onChange={(grade) => update(item.return_item_id, { grade })}
                />
                <Segmented
                  legend="Decision"
                  options={DECISIONS}
                  value={s.decision}
                  onChange={(decision) => update(item.return_item_id, { decision })}
                />
              </div>
              <label className="field">
                <span className="field__label field__label--quiet">Notes (optional)</span>
                <input
                  className="input input--sm"
                  maxLength={500}
                  value={s.notes}
                  onChange={(e) => update(item.return_item_id, { notes: e.target.value })}
                />
              </label>
              {missing && (
                <span className="field__error" role="alert">
                  Choose a grade and a decision.
                </span>
              )}
            </li>
          )
        })}
      </ul>

      <div className="summary-total">
        <span>Refund total</span>
        <strong>{complete ? formatInr(total) : '—'}</strong>
      </div>
      {complete && total > APPROVAL_THRESHOLD && (
        <Alert tone="warning" title="Needs finance approval">
          Refunds above ₹10,000 go to a finance reviewer before they are paid.
        </Alert>
      )}
      {error && (
        <Alert tone="danger" title="Inspection not saved">
          {error}
        </Alert>
      )}
      <div className="form-actions">
        <Button onClick={submit} loading={submitting}>
          Submit inspection
        </Button>
      </div>
    </Card>
  )
}

function ResultCard({ result }: { result: InspectionResultResponse }) {
  return (
    <Card title="Inspection saved">
      <Alert
        tone={
          result.status === 'rejected'
            ? 'danger'
            : result.needs_finance_approval
              ? 'warning'
              : 'success'
        }
        title={
          result.status === 'rejected'
            ? 'All items rejected: no refund'
            : result.needs_finance_approval
              ? `Refund of ${formatInr(result.refund_total)} sent for finance approval`
              : `Refund of ${formatInr(result.refund_total)} paid`
        }
      />
      <GradedItemsTable items={result.items} total={result.refund_total} />
      <div className="form-actions">
        <Link to="/warehouse" className="btn btn--primary">
          Next parcel
        </Link>
      </div>
    </Card>
  )
}
