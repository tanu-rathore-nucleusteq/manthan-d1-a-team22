import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState, type ReactNode } from 'react'

import { ApiError } from '../api/errors'
import { AuthContext } from './AuthContext'
import { getStoredSession, storeSession, type Session } from './session'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(getStoredSession)
  const queryClient = useQueryClient()

  // An expired token answers 401 on every staff call: sign out, so RequireRole sends the user
  // to the login page instead of leaving each screen in an error state.
  useEffect(() => {
    const signOutOnExpiry = (error: unknown) => {
      if (
        error instanceof ApiError &&
        error.status === 401 &&
        error.code !== 'invalid_credentials'
      ) {
        storeSession(null)
        setSession(null)
      }
    }
    const stopQueries = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error')
        signOutOnExpiry(event.action.error)
    })
    const stopMutations = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error')
        signOutOnExpiry(event.action.error)
    })
    return () => {
      stopQueries()
      stopMutations()
    }
  }, [queryClient])

  const value = useMemo(
    () => ({
      session,
      signIn: (next: Session) => {
        storeSession(next)
        setSession(next)
      },
      signOut: () => {
        storeSession(null)
        setSession(null)
      },
    }),
    [session],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
