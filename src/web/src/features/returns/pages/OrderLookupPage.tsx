import { PageHeader } from '../../../components/ui/PageHeader'

export function OrderLookupPage() {
  return (
    <>
      <PageHeader
        title="Start a return"
        subtitle="Enter your order number and the email you ordered with."
      />
      <form className="form" aria-label="Find your order" onSubmit={(e) => e.preventDefault()}>
        <label>
          Order number
          <input name="orderNumber" required autoComplete="off" />
        </label>
        <label>
          Email
          <input name="email" type="email" required autoComplete="email" />
        </label>
        <button type="submit">Find order</button>
      </form>
    </>
  )
}
