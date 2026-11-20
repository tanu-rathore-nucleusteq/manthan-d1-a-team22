import { Link, useLocation, useNavigate, useParams } from 'react-router'

import { getErrorMessage } from '../../../api/errors'
import { useToast } from '../../../components/toast/toastContext'
import { Alert } from '../../../components/ui/Alert'
import { StatusBadge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { ErrorState } from '../../../components/ui/ErrorState'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { useMarkShipped, useReturnDetail, useReturnLabel } from '../api'
import { ProofGate } from '../components/ProofGate'

export function ReturnLabelPage() {
  const { returnCode = '' } = useParams()
  return (
    <ProofGate returnCode={returnCode}>
      {(email) => <Label code={returnCode} email={email} />}
    </ProofGate>
  )
}

function Label({ code, email }: { code: string; email: string }) {
  const navigate = useNavigate()
  const toast = useToast()
  const state = useLocation().state as { created?: boolean; photoUploaded?: boolean } | null
  const justCreated = state?.created
  const label = useReturnLabel(code, email)
  const detail = useReturnDetail(code, email)
  const shipped = useMarkShipped(code)

  if (label.isPending || detail.isPending)
    return <LoadingState label="Preparing your label" lines={5} />
  if (label.isError) return <ErrorState error={label.error} onRetry={() => label.refetch()} />
  if (detail.isError) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />

  const awaitingShipment = detail.data.status === 'approved'
  const qrSrc = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(label.data.qr_svg)}`

  const markShipped = () =>
    shipped.mutate(email, {
      onSuccess: () => {
        toast({ tone: 'success', title: 'Thanks! Your return is on its way.' })
        navigate(`/returns/${code}`)
      },
    })

  return (
    <>
      <PageHeader
        title="Your return label"
        subtitle={`Return ${label.data.return_code}`}
        meta={<StatusBadge status={detail.data.status} />}
        actions={
          <Button variant="secondary" onClick={() => window.print()}>
            Print label
          </Button>
        }
      />

      {justCreated && (
        <Alert tone="success" title="Return created">
          All items were approved for return. Print this label and attach it to your parcel.
        </Alert>
      )}
      {justCreated && state?.photoUploaded === false && (
        <Alert tone="warning" title="Your photo didn't upload">
          Your return is saved. Pack the item as it is; the warehouse will check it on arrival.
        </Alert>
      )}

      <div className="label-layout">
        <section className="shipping-label" aria-label="Shipping label">
          <div className="shipping-label__qr">
            {/* Rendered as an image, so markup inside the SVG can never run as code. */}
            <img
              src={qrSrc}
              alt={`QR code for return ${label.data.return_code}`}
              width={180}
              height={180}
            />
          </div>
          <div className="shipping-label__details">
            <span className="shipping-label__caption">Return code</span>
            <span className="shipping-label__code">{label.data.return_code}</span>
            <span className="shipping-label__caption">Ship to</span>
            <address>{label.data.ship_to}</address>
            <span className="shipping-label__caption">Items</span>
            <ul className="plain-list">
              {detail.data.items.map((i) => (
                <li key={i.return_item_id}>
                  {i.product_name} × {i.quantity}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <Card title="What to do next" className="no-print">
          <ol className="steps-list">
            <li>
              <strong>Pack the items</strong>
              <span>Use the original packaging if you still have it.</span>
            </li>
            <li>
              <strong>Attach this label</strong>
              <span>Make sure the QR code is flat and easy to scan.</span>
            </li>
            <li>
              <strong>Hand it to the courier</strong>
              <span>Then let us know below so we can track it.</span>
            </li>
          </ol>
          {shipped.isError && (
            <Alert tone="danger" title="Couldn't update your return">
              {getErrorMessage(shipped.error)}
            </Alert>
          )}
          {awaitingShipment ? (
            <Button block onClick={markShipped} loading={shipped.isPending}>
              I've shipped it
            </Button>
          ) : (
            <Link to={`/returns/${code}`} className="btn btn--secondary btn--block">
              Track this return
            </Link>
          )}
        </Card>
      </div>
    </>
  )
}
