import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { ErrorState } from '../components/ui/ErrorState'
import { useAuth } from './AuthContext'
import type { Role } from './roles'

/** Guards staff screens. Customers use the public return flow and never log in. */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { session } = useAuth()
  const location = useLocation()

  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!roles.includes(session.role)) {
    return <ErrorState title="No access" message="Your role cannot open this page." />
  }
  return children
}
