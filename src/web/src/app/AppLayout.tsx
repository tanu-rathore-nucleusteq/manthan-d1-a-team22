import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router'

import { USE_MOCKS } from '../api/backend'
import { resetMockData } from '../api/mock/mockBackend'
import { useAuth } from '../auth/AuthContext'
import {
  HOME_BY_ROLE,
  NAV_BY_ROLE,
  ROLE_LABEL,
  WORKSPACE_BY_ROLE,
  type NavItem,
} from '../auth/roles'
import type { Session } from '../auth/session'
import { Icon } from '../components/ui/Icon'
import { ThemeToggle } from '../components/ui/ThemeToggle'

const CUSTOMER_NAV: NavItem[] = [
  { to: '/returns', label: 'Start a return', icon: 'package', end: true },
  { to: '/returns/track', label: 'Track a return', icon: 'search' },
]

function Brand({ to, inverted }: { to: string; inverted?: boolean }) {
  return (
    <Link to={to} className={inverted ? 'brand brand--inverted' : 'brand'}>
      <span className="brand__mark" aria-hidden="true">
        <Icon name="rotateCcw" size={17} strokeWidth={2.4} />
      </span>
      <span className="brand__name">
        Return<span className="brand__accent">Right</span>
      </span>
    </Link>
  )
}

function initials(name: string) {
  return name
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('')
}

export function AppLayout() {
  const { session, signOut } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

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

  return session ? (
    <StaffShell session={session} onSignOut={handleSignOut} onReset={handleReset} />
  ) : (
    <CustomerShell onReset={handleReset} />
  )
}

function SkipLink() {
  return (
    <a className="skip-link" href="#main">
      Skip to content
    </a>
  )
}

function StaffShell({
  session,
  onSignOut,
  onReset,
}: {
  session: Session
  onSignOut: () => void
  onReset: () => void
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const nav = NAV_BY_ROLE[session.role]
  const close = () => setMenuOpen(false)

  return (
    <div className={menuOpen ? 'app app--menu-open' : 'app'}>
      <SkipLink />
      <aside className="sidebar" id="sidebar" aria-label="Workspace">
        <div className="sidebar__brand">
          <Brand to={HOME_BY_ROLE[session.role]} inverted />
        </div>

        <nav aria-label="Main" className="sidebar__nav">
          <span className="sidebar__section">{WORKSPACE_BY_ROLE[session.role]}</span>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className="side-link"
              onClick={close}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {USE_MOCKS && (
          <div className="sidebar__demo">
            <span className="sidebar__demo-title">
              <Icon name="database" size={15} />
              Demo data
            </span>
            <p>Synthetic data, kept until this tab closes.</p>
            <button type="button" className="sidebar__demo-btn" onClick={onReset}>
              <Icon name="rotateCcw" size={14} />
              Reset demo data
            </button>
          </div>
        )}

        <div className="sidebar__user">
          <span className="avatar" aria-hidden="true">
            {initials(session.name)}
          </span>
          <span className="sidebar__user-text">
            <span className="sidebar__user-name">{session.name}</span>
            <span className="sidebar__user-role">{ROLE_LABEL[session.role]}</span>
          </span>
          <button
            type="button"
            className="icon-btn icon-btn--inverted"
            onClick={onSignOut}
            aria-label="Sign out"
            title="Sign out"
          >
            <Icon name="logOut" />
          </button>
        </div>
      </aside>

      <button
        type="button"
        className="sidebar-scrim"
        aria-label="Close menu"
        tabIndex={menuOpen ? 0 : -1}
        onClick={close}
      />

      <div className="app__body">
        <header className="appbar">
          <button
            type="button"
            className="icon-btn appbar__menu"
            aria-label="Open menu"
            aria-controls="sidebar"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
          >
            <Icon name="menu" />
          </button>
          <div className="appbar__context">
            <span className="appbar__workspace">{WORKSPACE_BY_ROLE[session.role]}</span>
            <Icon name="chevronRight" size={14} className="appbar__sep" />
            <span className="appbar__role">{ROLE_LABEL[session.role]}</span>
          </div>
          <ThemeToggle />
        </header>

        <main id="main" tabIndex={-1} className="main main--staff">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function CustomerShell({ onReset }: { onReset: () => void }) {
  return (
    <div className="shell">
      <SkipLink />
      <header className="topbar">
        <div className="topbar__inner">
          <Brand to="/returns" />
          <nav aria-label="Main" className="topbar__nav">
            {CUSTOMER_NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className="nav-link">
                <Icon name={item.icon} size={16} />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="topbar__actions">
            <ThemeToggle />
            <NavLink to="/login" className="btn btn--secondary btn--sm">
              <Icon name="logIn" size={16} />
              Staff sign in
            </NavLink>
            <NavLink to="/signup" className="btn btn--primary btn--sm">
              <Icon name="users" size={16} />
              Sign up
            </NavLink>
          </div>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="footer__inner">
          <div className="footer__brand">
            <Brand to="/returns" />
            <span>Returns and refunds, tracked at every step.</span>
          </div>
          <ul className="footer__trust">
            <li>
              <Icon name="shieldCheck" size={16} />
              Your order email proves ownership
            </li>
            <li>
              <Icon name="printer" size={16} />
              Printable QR return label
            </li>
            <li>
              <Icon name="wallet" size={16} />
              Refund to card or store credit
            </li>
          </ul>
          {USE_MOCKS && (
            <span className="footer__demo">
              <span className="env-pill">
                <span className="env-pill__dot" aria-hidden="true" />
                Demo mode
              </span>
              Synthetic data, kept until this tab closes.
              <button type="button" className="link-btn" onClick={onReset}>
                Reset demo data
              </button>
            </span>
          )}
        </div>
      </footer>
    </div>
  )
}
