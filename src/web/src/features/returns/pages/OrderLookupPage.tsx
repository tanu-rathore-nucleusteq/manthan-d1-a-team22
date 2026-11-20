import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { USE_MOCKS } from '../../../api/backend'
import { getErrorMessage } from '../../../api/errors'
import { DEMO_ORDERS } from '../../../api/mock/seed'
import { Alert } from '../../../components/ui/Alert'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { TextField } from '../../../components/ui/Field'
import { useOrderLookup } from '../api'

const ORDER_NUMBER = /^[A-Za-z0-9-]{4,32}$/
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

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
    <div className="split">
      <div className="split__main">
        <p className="eyebrow">Returns and refunds</p>
        <h1 className="display">Return an item</h1>
        <p className="lead">
          Find your order to see which items can be returned. You'll get a printable label and can
          track your refund at every step.
        </p>

        <Card>
          <form className="stack" onSubmit={submit} noValidate aria-label="Find your order">
            {lookup.isError && (
              <Alert tone="danger" title="Order not found">
                {getErrorMessage(lookup.error)} Check both fields and try again.
              </Alert>
            )}
            <div className="grid-2">
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
            </div>
            <div>
              <Button type="submit" loading={lookup.isPending}>
                Find order
              </Button>
            </div>
          </form>
        </Card>

        {USE_MOCKS && (
          <section className="demo-panel" aria-label="Demo orders">
            <h2>Demo orders</h2>
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
                    <code>{o.orderNumber}</code>
                    <span>{o.note}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <aside className="split__aside">
        <Card title="How it works">
          <ol className="steps-list">
            <li>
              <strong>Find your order</strong>
              <span>We check each item against the return policy and tell you why.</span>
            </li>
            <li>
              <strong>Ship it with your label</strong>
              <span>Print the QR label, pack the items, and tell us when it's on its way.</span>
            </li>
            <li>
              <strong>Get your refund</strong>
              <span>We inspect the items and refund to your original payment or store credit.</span>
            </li>
          </ol>
        </Card>
        <Card title="Return policy">
          <ul className="policy-list">
            <li>30 days from delivery for most items</li>
            <li>10 days for electronics</li>
            <li>Innerwear and perishables can't be returned</li>
            <li>Items that come back used or damaged (grade C) are refunded at 50%</li>
          </ul>
        </Card>
      </aside>
    </div>
  )
}
