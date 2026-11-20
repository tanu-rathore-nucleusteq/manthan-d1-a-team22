import { Link } from 'react-router'

import { EmptyState } from '../components/ui/EmptyState'
import { Icon } from '../components/ui/Icon'

export function NotFoundPage() {
  return (
    <EmptyState title="Page not found" icon="search">
      <p>The page you're looking for doesn't exist or has moved.</p>
      <Link to="/returns" className="btn btn--primary btn--sm state__action">
        <Icon name="arrowLeft" size={15} />
        Go to start a return
      </Link>
    </EmptyState>
  )
}
