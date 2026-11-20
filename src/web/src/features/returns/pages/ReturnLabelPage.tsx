import { useParams } from 'react-router'

import { EmptyState } from '../../../components/ui/EmptyState'
import { PageHeader } from '../../../components/ui/PageHeader'

export function ReturnLabelPage() {
  const { returnId } = useParams()

  return (
    <>
      <PageHeader title="Your return label" subtitle={`Return ${returnId}`} />
      <EmptyState title="QR label">
        <p>Print this label, attach it to the parcel, then tell us you have shipped it.</p>
      </EmptyState>
    </>
  )
}
