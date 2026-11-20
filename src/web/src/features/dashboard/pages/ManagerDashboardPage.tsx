import { EmptyState } from '../../../components/ui/EmptyState'
import { PageHeader } from '../../../components/ui/PageHeader'

const PANELS = [
  'Return rate by category',
  'Top return reasons',
  'Average cycle time',
  'Flagged customers',
]

export function ManagerDashboardPage() {
  return (
    <>
      <PageHeader title="Returns dashboard" />
      <div className="grid">
        {PANELS.map((panel) => (
          <section key={panel} className="card" aria-label={panel}>
            <h2>{panel}</h2>
            <EmptyState title="No data yet" />
          </section>
        ))}
      </div>
    </>
  )
}
