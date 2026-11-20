import type { ReactNode } from 'react'
import { Link, Navigate, useLocation } from 'react-router'

import { EmptyState } from '../components/ui/EmptyState'
import { useAuth } from './AuthContext'
import { HOME_BY_ROLE, ROLE_LABEL, type Role } from './roles'

/** Guards staff screens. Customers use the public return flow and never log in. */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { session } = useAuth()
  const location = useLocation()

  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!roles.includes(session.role)) {
    return (
      <EmptyState title="You don't have access to this page">
        <p>
          Signed in as {ROLE_LABEL[session.role]}.{' '}
          <Link to={HOME_BY_ROLE[session.role]}>Go to your work queue</Link>
        </p>
      </EmptyState>
    )
  }
  return children
}
