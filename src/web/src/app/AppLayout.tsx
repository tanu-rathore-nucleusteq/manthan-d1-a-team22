import { Link, NavLink, Outlet } from 'react-router'

import { useAuth } from '../auth/AuthContext'
import { HOME_BY_ROLE } from '../auth/roles'

export function AppLayout() {
  const { session, signOut } = useAuth()

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="app-header">
        <Link to="/" className="brand">
          ReturnRight
        </Link>
        <nav aria-label="Main">
          <NavLink to="/returns">Start a return</NavLink>
          {session ? (
            <>
              <NavLink to={HOME_BY_ROLE[session.role]}>My work</NavLink>
              <button type="button" onClick={signOut}>
                Sign out {session.name}
              </button>
            </>
          ) : (
            <NavLink to="/login">Staff sign in</NavLink>
          )}
        </nav>
      </header>
      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  )
}
