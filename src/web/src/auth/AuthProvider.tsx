import { useMemo, useState, type ReactNode } from 'react'

import { AuthContext } from './AuthContext'
import { getStoredSession, storeSession, type Session } from './session'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(getStoredSession)

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
