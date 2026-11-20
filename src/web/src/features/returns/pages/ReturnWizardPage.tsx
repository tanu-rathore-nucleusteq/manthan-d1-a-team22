import { useParams } from 'react-router'

import { EmptyState } from '../../../components/ui/EmptyState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { Stepper } from '../components/Stepper'

export function ReturnWizardPage() {
  const { orderId } = useParams()

  return (
    <>
      <PageHeader title="Return items" subtitle={`Order ${orderId}`} />
      <Stepper current={0} />
      <EmptyState title="Item selection">
        <p>Eligible items and refusal reasons from the eligibility engine appear here.</p>
      </EmptyState>
    </>
  )
}
