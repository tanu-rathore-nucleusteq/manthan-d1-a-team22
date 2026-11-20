import { useParams } from 'react-router'

import { PageHeader } from '../../../components/ui/PageHeader'
import { StatusTimeline } from '../components/StatusTimeline'

export function ReturnStatusPage() {
  const { returnId } = useParams()

  return (
    <>
      <PageHeader title="Return status" subtitle={`Return ${returnId}`} />
      <StatusTimeline status="Requested" />
    </>
  )
}
