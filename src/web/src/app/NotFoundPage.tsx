import { Link } from 'react-router'

import { EmptyState } from '../components/ui/EmptyState'

export function NotFoundPage() {
  return (
    <EmptyState title="Page not found">
      <Link to="/returns">Go to start a return</Link>
    </EmptyState>
  )
}
