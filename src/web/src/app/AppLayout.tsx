import { useQueryClient } from '@tanstack/react-query'
import { Link, NavLink, Outlet, useNavigate } from 'react-router'

import { USE_MOCKS } from '../api/backend'
import { resetMockData } from '../api/mock/mockBackend'
import { useAuth } from '../auth/AuthContext'
import { HOME_BY_ROLE, NAV_BY_ROLE, ROLE_LABEL } from '../auth/roles'
import { Button } from '../components/ui/Button'

const CUSTOMER_NAV = [
  { to: '/returns', label: 'Start a return', end: true },
  { to: '/returns/track', label: 'Track a return' },
]

export function AppLayout() {
  const { session, signOut } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const nav = session ? NAV_BY_ROLE[session.role] : CUSTOMER_NAV

  const handleSignOut = () => {
    signOut()
    queryClient.clear()
    navigate('/login')
  }

  const handleReset = () => {
    resetMockData()
    queryClient.clear()
    navigate(session ? HOME_BY_ROLE[session.role] : '/returns')
  }

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <div className="topbar__inner">
          <Link to={session ? HOME_BY_ROLE[session.role] : '/returns'} className="brand">
            <span className="brand__mark" aria-hidden="true">
              R
            </span>
            ReturnRight
          </Link>
          <nav aria-label="Main" className="topbar__nav">
            {nav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className="nav-link">
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="topbar__user">
            {session ? (
              <>
                <span className="user-chip">
                  <span className="user-chip__name">{session.name}</span>
                  <span className="user-chip__role">{ROLE_LABEL[session.role]}</span>
                </span>
                <Button variant="ghost" size="sm" onClick={handleSignOut}>
                  Sign out
                </Button>
              </>
            ) : (
              <NavLink to="/login" className="nav-link">
                Staff sign in
              </NavLink>
            )}
          </div>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="footer__inner">
          <span>ReturnRight · returns and refunds</span>
          {USE_MOCKS && (
            <span className="footer__demo">
              Demo mode: synthetic data, kept until this tab closes.
              <Button variant="ghost" size="sm" onClick={handleReset}>
                Reset demo data
              </Button>
            </span>
          )}
        </div>
      </footer>
    </div>
  )
}
