import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { USE_MOCKS } from '../../../api/backend'
import { getErrorMessage } from '../../../api/errors'
import { DEMO_ORDERS } from '../../../api/mock/seed'
import { Alert } from '../../../components/ui/Alert'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { TextField } from '../../../components/ui/Field'
import { Icon, type IconName } from '../../../components/ui/Icon'
import { useOrderLookup } from '../api'

const ORDER_NUMBER = /^[A-Za-z0-9-]{4,32}$/
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

const STEPS: { icon: IconName; title: string; body: string }[] = [
  {
    icon: 'search',
    title: 'Find your order',
    body: 'We check each item against the return policy and tell you why.',
  },
  {
    icon: 'printer',
    title: 'Ship it with your label',
    body: "Print the QR label, pack the items, and tell us when it's on its way.",
  },
  {
    icon: 'wallet',
    title: 'Get your refund',
    body: 'We inspect the items and refund to your original payment or store credit.',
  },
]

const POLICY = [
  '30 days from delivery for most items',
  '10 days for electronics',
  "Innerwear and perishables can't be returned",
  'Items that come back used or damaged (grade C) are refunded at 50%',
]

export function OrderLookupPage() {
  const navigate = useNavigate()
  const lookup = useOrderLookup()
  const [orderNumber, setOrderNumber] = useState('')
  const [email, setEmail] = useState('')
  const [errors, setErrors] = useState<{ orderNumber?: string; email?: string }>({})

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const next = {
      orderNumber: ORDER_NUMBER.test(orderNumber.trim())
        ? undefined
        : 'Enter the order number from your confirmation email, e.g. RR-10021.',
      email: EMAIL.test(email.trim()) ? undefined : 'Enter a valid email address.',
    }
    setErrors(next)
    if (next.orderNumber || next.email) return
    const body = {
      order_number: orderNumber.trim().toUpperCase(),
      email: email.trim().toLowerCase(),
    }
    lookup.mutate(body, {
      onSuccess: () =>
        navigate(`/returns/new/${body.order_number}`, { state: { email: body.email } }),
    })
  }

  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero__text">
          <span className="pill">
            <Icon name="rotateCcw" size={14} />
            Returns and refunds
          </span>
          <h1 id="hero-title" className="display">
            Return an item in a few minutes
          </h1>
          <p className="lead">
            Find your order to see which items can be returned. You'll get a printable label and can
            track your refund at every step.
          </p>
          <ul className="hero__points">
            <li>
              <Icon name="check" size={16} strokeWidth={2.6} />
              Instant eligibility check
            </li>
            <li>
              <Icon name="check" size={16} strokeWidth={2.6} />
              Printable QR label
            </li>
            <li>
              <Icon name="check" size={16} strokeWidth={2.6} />
              Live refund tracking
            </li>
          </ul>
        </div>

        <div className="hero__form card card--raised">
          <div className="card__header">
            <div>
              <h2 className="card__title">Find your order</h2>
              <p className="card__description">Use the details from your confirmation email.</p>
            </div>
          </div>
          <div className="card__body">
            <form className="stack" onSubmit={submit} noValidate aria-label="Find your order">
              {lookup.isError && (
                <Alert tone="danger" title="Order not found">
                  {getErrorMessage(lookup.error)} Check both fields and try again.
                </Alert>
              )}
              <TextField
                label="Order number"
                name="orderNumber"
                placeholder="RR-10021"
                autoComplete="off"
                value={orderNumber}
                error={errors.orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
              />
              <TextField
                label="Email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                error={errors.email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Button type="submit" block loading={lookup.isPending}>
                {!lookup.isPending && <Icon name="search" size={16} />}
                Find order
              </Button>
            </form>

            {USE_MOCKS && (
              <section className="demo-panel demo-panel--inline" aria-label="Demo orders">
                <div className="demo-panel__head">
                  <h2>Demo orders</h2>
                  <span className="muted">Click to fill</span>
                </div>
                <ul className="demo-list">
                  {DEMO_ORDERS.map((o) => (
                    <li key={o.orderNumber}>
                      <button
                        type="button"
                        className="demo-list__item"
                        onClick={() => {
                          setOrderNumber(o.orderNumber)
                          setEmail(o.email)
                          setErrors({})
                        }}
                      >
                        <span className="demo-list__icon">
                          <Icon name="package" size={16} />
                        </span>
                        <span className="demo-list__text">
                          <code>{o.orderNumber}</code>
                          <span>{o.note}</span>
                        </span>
                        <Icon name="chevronRight" size={16} className="demo-list__chevron" />
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </div>
      </section>

      <section className="info-grid" aria-label="About returns">
        <Card title="How it works">
          <ol className="feature-steps">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <span className="feature-steps__icon">
                  <Icon name={s.icon} size={20} />
                </span>
                <span className="feature-steps__text">
                  <span className="feature-steps__index">Step {i + 1}</span>
                  <strong>{s.title}</strong>
                  <span>{s.body}</span>
                </span>
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Return policy">
          <ul className="check-list">
            {POLICY.map((p) => (
              <li key={p}>
                <Icon name="checkCircle" size={18} />
                {p}
              </li>
            ))}
          </ul>
        </Card>
      </section>
    </>
  )
}
