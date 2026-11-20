import type { Role } from './roles'

export interface Session {
  token: string
  role: Role
  name: string
}

const KEY = 'returnright.session'

// sessionStorage: the login ends when the tab closes, which suits shared warehouse laptops.
export function getStoredSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function storeSession(session: Session | null): void {
  try {
    if (session) sessionStorage.setItem(KEY, JSON.stringify(session))
    else sessionStorage.removeItem(KEY)
  } catch {
    // Storage blocked (private mode): the session lives in memory only.
  }
}
