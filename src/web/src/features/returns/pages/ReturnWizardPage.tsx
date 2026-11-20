import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router'

import { getErrorMessage } from '../../../api/errors'
import type { ItemEligibilityResponse, RefundMethod, ReturnReason } from '../../../api/types'
import { Alert } from '../../../components/ui/Alert'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { ErrorState } from '../../../components/ui/ErrorState'
import { TextAreaField } from '../../../components/ui/Field'
import { Icon } from '../../../components/ui/Icon'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { formatDate, formatInr } from '../../../lib/format'
import { REASON_LABEL, REFUND_METHOD_LABEL } from '../../../lib/labels'
import { useCreateReturn, useOrder } from '../api'
import { Stepper } from '../components/Stepper'
import { saveProof } from '../customerProof'

const STEPS = ['Items', 'Reason', 'Photo', 'Refund', 'Review'] as const
const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const PHOTO_MAX_BYTES = 5 * 1024 * 1024
const APPROVAL_THRESHOLD = 10_000

const REFUND_HELP: Record<RefundMethod, string> = {
  original_payment: 'Paid back to the card, UPI or bank account you used, after inspection.',
  store_credit: 'Added to your ReturnRight balance as soon as the items pass inspection.',
}

export function ReturnWizardPage() {
  const { orderNumber = '' } = useParams()
  const email = (useLocation().state as { email?: string } | null)?.email ?? null
  const order = useOrder(orderNumber, email)

  if (!email) return <Navigate to="/returns" replace />

  return (
    <>
      <PageHeader
        title="Return items"
        subtitle={`Order ${orderNumber}`}
        back={{ to: '/returns', label: 'Find a different order' }}
      />
      {order.isPending && <LoadingState label="Checking your order" lines={4} />}
      {order.isError && <ErrorState error={order.error} onRetry={() => order.refetch()} />}
      {order.data && (
        <Wizard
          orderNumber={order.data.order_number}
          deliveredOn={order.data.delivered_on}
          items={order.data.items}
          email={email}
        />
      )}
    </>
  )
}

interface WizardProps {
  orderNumber: string
  deliveredOn: string | null
  items: ItemEligibilityResponse[]
  email: string
}

function Wizard({ orderNumber, deliveredOn, items, email }: WizardProps) {
  const navigate = useNavigate()
  const create = useCreateReturn()
  const [step, setStep] = useState(0)
  const [selected, setSelected] = useState<Record<number, number>>({})
  const [reason, setReason] = useState<ReturnReason | null>(null)
  const [details, setDetails] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [method, setMethod] = useState<RefundMethod | null>(null)
  const [error, setError] = useState<string | null>(null)

  const eligible = items.filter((i) => i.eligible)
  const chosen = items.filter((i) => selected[i.order_item_id])
  const estimate = chosen.reduce(
    (sum, i) => sum + Number(i.unit_price) * selected[i.order_item_id],
    0,
  )

  const previewUrl = useMemo(() => (photo ? URL.createObjectURL(photo) : null), [photo])
  useEffect(() => () => void (previewUrl && URL.revokeObjectURL(previewUrl)), [previewUrl])

  const validate = (index: number): string | null => {
    if (index === 0 && chosen.length === 0) return 'Select at least one item to return.'
    if (index === 1 && !reason) return 'Choose a reason for the return.'
    if (index === 1 && reason === 'other' && !details.trim())
      return 'Tell us a little more about the reason.'
    if (index === 2 && !photo) return 'Add a photo of the items.'
    if (index === 3 && !method) return 'Choose how you would like to be refunded.'
    return null
  }

  const next = () => {
    const problem = validate(step)
    setError(problem)
    if (!problem) setStep(step + 1)
  }

  const submit = () => {
    create.mutate(
      {
        body: {
          order_number: orderNumber,
          email,
          items: chosen.map((i) => ({
            order_item_id: i.order_item_id,
            quantity: selected[i.order_item_id],
          })),
          reason: reason!,
          reason_details: details.trim() || null,
          refund_method: method!,
        },
        photo: photo!,
      },
      {
        onSuccess: (created) => {
          saveProof(created.return_code, email)
          navigate(`/returns/${created.return_code}/label`, {
            replace: true,
            state: { created: true },
          })
        },
      },
    )
  }

  const toggle = (item: ItemEligibilityResponse) =>
    setSelected((current) => {
      const copy = { ...current }
      if (copy[item.order_item_id]) delete copy[item.order_item_id]
      else copy[item.order_item_id] = 1
      return copy
    })

  const choosePhoto = (file: File | undefined) => {
    if (!file) return
    if (!PHOTO_TYPES.includes(file.type)) return setError('Use a JPG, PNG or WebP image.')
    if (file.size > PHOTO_MAX_BYTES) return setError('The photo must be 5 MB or smaller.')
    setError(null)
    setPhoto(file)
  }

  if (eligible.length === 0) {
    return (
      <div className="stack">
        <Alert tone="warning" title="Nothing in this order can be returned">
          Each item below shows the reason.
        </Alert>
        <ItemList items={items} selected={selected} onToggle={toggle} onQuantity={() => {}} />
      </div>
    )
  }

  return (
    <div className="wizard">
      <div className="wizard__main">
        <Stepper steps={STEPS} current={step} onSelect={(i) => setStep(i)} />

        {error && (
          <Alert tone="danger" title="Check this step">
            {error}
          </Alert>
        )}

        {step === 0 && (
          <Card
            title="Which items are you returning?"
            description={deliveredOn ? `Delivered on ${formatDate(deliveredOn)}.` : undefined}
          >
            <ItemList
              items={items}
              selected={selected}
              onToggle={toggle}
              onQuantity={(id, qty) => setSelected((s) => ({ ...s, [id]: qty }))}
            />
          </Card>
        )}

        {step === 1 && (
          <Card title="Why are you returning them?">
            <fieldset className="choice-list">
              <legend className="visually-hidden">Return reason</legend>
              {(Object.keys(REASON_LABEL) as ReturnReason[]).map((value) => (
                <label key={value} className="choice">
                  <input
                    type="radio"
                    name="reason"
                    checked={reason === value}
                    onChange={() => setReason(value)}
                  />
                  <span className="choice__label">{REASON_LABEL[value]}</span>
                </label>
              ))}
            </fieldset>
            <TextAreaField
              label={
                reason === 'other' ? 'Tell us more' : 'Anything else we should know? (optional)'
              }
              maxLength={500}
              rows={3}
              value={details}
              hint={`${details.length}/500`}
              onChange={(e) => setDetails(e.target.value)}
            />
          </Card>
        )}

        {step === 2 && (
          <Card
            title="Add a photo"
            description="A clear photo of the items helps the warehouse inspect them faster."
          >
            <label className="dropzone">
              <input
                type="file"
                accept={PHOTO_TYPES.join(',')}
                className="visually-hidden"
                onChange={(e) => choosePhoto(e.target.files?.[0])}
              />
              {previewUrl ? (
                <img src={previewUrl} alt="Selected item" className="dropzone__preview" />
              ) : (
                <span className="dropzone__icon">
                  <Icon name="upload" size={26} />
                </span>
              )}
              <span className="dropzone__text">
                <strong>{photo ? photo.name : 'Choose a photo'}</strong>
                <span className="muted">JPG, PNG or WebP, up to 5 MB</span>
              </span>
            </label>
          </Card>
        )}

        {step === 3 && (
          <Card title="How would you like your refund?">
            <fieldset className="choice-list">
              <legend className="visually-hidden">Refund method</legend>
              {(Object.keys(REFUND_METHOD_LABEL) as RefundMethod[]).map((value) => (
                <label key={value} className="choice choice--card">
                  <input
                    type="radio"
                    name="method"
                    checked={method === value}
                    onChange={() => setMethod(value)}
                  />
                  <span>
                    <span className="choice__label">{REFUND_METHOD_LABEL[value]}</span>
                    <span className="choice__hint">{REFUND_HELP[value]}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          </Card>
        )}

        {step === 4 && (
          <Card title="Review your return">
            <dl className="review">
              <ReviewRow label="Items" onEdit={() => setStep(0)}>
                <ul className="plain-list">
                  {chosen.map((i) => (
                    <li key={i.order_item_id}>
                      {i.product_name} × {selected[i.order_item_id]}
                    </li>
                  ))}
                </ul>
              </ReviewRow>
              <ReviewRow label="Reason" onEdit={() => setStep(1)}>
                {REASON_LABEL[reason!]}
                {details.trim() && <p className="muted">{details.trim()}</p>}
              </ReviewRow>
              <ReviewRow label="Photo" onEdit={() => setStep(2)}>
                {photo?.name}
              </ReviewRow>
              <ReviewRow label="Refund to" onEdit={() => setStep(3)}>
                {REFUND_METHOD_LABEL[method!]}
              </ReviewRow>
            </dl>
            {create.isError && (
              <Alert tone="danger" title="We couldn't create your return">
                {getErrorMessage(create.error)}
              </Alert>
            )}
          </Card>
        )}

        <div className="wizard__nav">
          {step > 0 ? (
            <Button
              variant="secondary"
              onClick={() => setStep(step - 1)}
              disabled={create.isPending}
            >
              Back
            </Button>
          ) : (
            <span />
          )}
          {step < STEPS.length - 1 ? (
            <Button onClick={next}>Continue</Button>
          ) : (
            <Button onClick={submit} loading={create.isPending}>
              Submit return
            </Button>
          )}
        </div>
      </div>

      <aside className="wizard__aside">
        <Card title="Summary">
          {chosen.length === 0 ? (
            <p className="muted">No items selected yet.</p>
          ) : (
            <ul className="summary-list">
              {chosen.map((i) => (
                <li key={i.order_item_id}>
                  <span>
                    {i.product_name} <span className="muted">× {selected[i.order_item_id]}</span>
                  </span>
                  <span>{formatInr(Number(i.unit_price) * selected[i.order_item_id])}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="summary-total">
            <span>Estimated refund</span>
            <strong>{formatInr(estimate)}</strong>
          </div>
          <p className="fine-print">
            Final amount is set at inspection: items graded C are refunded at 50%.
            {estimate > APPROVAL_THRESHOLD &&
              ' Refunds above ₹10,000 are also checked by our finance team.'}
          </p>
        </Card>
      </aside>
    </div>
  )
}

function ItemList({
  items,
  selected,
  onToggle,
  onQuantity,
}: {
  items: ItemEligibilityResponse[]
  selected: Record<number, number>
  onToggle: (item: ItemEligibilityResponse) => void
  onQuantity: (id: number, qty: number) => void
}) {
  return (
    <ul className="item-list">
      {items.map((item) => {
        const qty = selected[item.order_item_id]
        return (
          <li key={item.order_item_id} className={item.eligible ? 'item' : 'item item--disabled'}>
            <label className="item__select">
              <input
                type="checkbox"
                checked={Boolean(qty)}
                disabled={!item.eligible}
                onChange={() => onToggle(item)}
                aria-describedby={`reason-${item.order_item_id}`}
              />
              <span className="item__body">
                <span className="item__name">{item.product_name}</span>
                <span className="item__meta">
                  {item.category} · {formatInr(item.unit_price)} each · ordered {item.quantity}
                </span>
                <span id={`reason-${item.order_item_id}`} className="item__reason">
                  <Badge tone={item.eligible ? 'success' : 'danger'}>
                    {item.eligible ? 'Returnable' : 'Not returnable'}
                  </Badge>
                  {item.reason}
                </span>
              </span>
            </label>
            {qty && item.quantity > 1 ? (
              <label className="item__qty">
                <span className="visually-hidden">Quantity of {item.product_name}</span>
                <select
                  className="input input--sm"
                  value={qty}
                  onChange={(e) => onQuantity(item.order_item_id, Number(e.target.value))}
                >
                  {Array.from({ length: item.quantity }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}

function ReviewRow({
  label,
  onEdit,
  children,
}: {
  label: string
  onEdit: () => void
  children: ReactNode
}) {
  return (
    <div className="review__row">
      <dt>{label}</dt>
      <dd>{children}</dd>
      <dd className="review__edit">
        <Button
          variant="ghost"
          size="sm"
          onClick={onEdit}
          aria-label={`Edit ${label.toLowerCase()}`}
        >
          Edit
        </Button>
      </dd>
    </div>
  )
}
