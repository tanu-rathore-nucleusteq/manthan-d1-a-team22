import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { useMutation } from '@tanstack/react-query'

import { backend, USE_MOCKS } from '../../api/backend'
import { getErrorMessage } from '../../api/errors'
import { DEMO_PASSWORD, DEMO_STAFF } from '../../api/mock/seed'
import type { LoginRequest } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { HOME_BY_ROLE } from '../../auth/roles'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { TextField } from '../../components/ui/Field'
import { Icon, type IconName } from '../../components/ui/Icon'

const DEMO_ICON: Record<string, IconName> = {
  warehouse_agent: 'clipboardCheck',
  finance_reviewer: 'shieldCheck',
  operations_manager: 'dashboard',
}

const FEATURES: { icon: IconName; title: string; body: string }[] = [
  {
    icon: 'clipboardCheck',
    title: 'Warehouse inspection',
    body: 'Scan labels, grade every item and settle refunds in one pass.',
  },
  {
    icon: 'shieldCheck',
    title: 'Finance approvals',
    body: 'High-value refunds wait for review and are never paid twice.',
  },
  {
    icon: 'barChart',
    title: 'Operations insight',
    body: 'Return rates, top reasons and flagged customers at a glance.',
  },
]

export function LoginPage() {
  const { session, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  const [form, setForm] = useState<LoginRequest>({ username: '', password: '' })

  const login = useMutation({
    mutationFn: (body: LoginRequest) => backend.login(body),
    onSuccess: (token, body) => {
      signIn({ token: token.access_token, role: token.role, name: body.username })
      navigate(from ?? HOME_BY_ROLE[token.role], { replace: true })
    },
  })

  if (session && !login.isPending) return <Navigate to={HOME_BY_ROLE[session.role]} replace />

  const submit = (e: FormEvent) => {
    e.preventDefault()
    login.mutate({ username: form.username.trim(), password: form.password })
  }

  return (
    <div className="auth">
      <section className="auth__panel" aria-labelledby="auth-panel-title">
        <span className="auth__badge">
          <Icon name="users" size={14} />
          Staff workspace
        </span>
        <h2 id="auth-panel-title" className="auth__panel-title">
          Every return, from label scan to refund, in one place.
        </h2>
        <ul className="auth__features">
          {FEATURES.map((f) => (
            <li key={f.title}>
              <span className="auth__feature-icon">
                <Icon name={f.icon} size={18} />
              </span>
              <span>
                <strong>{f.title}</strong>
                <span>{f.body}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="auth__form" aria-labelledby="auth-title">
        <div className="auth__form-head">
          <h1 id="auth-title" className="auth__title">
            Sign in
          </h1>
          <p className="muted">
            For warehouse, finance and operations staff. New here?{' '}
            <Link to="/signup">Create an account</Link>
          </p>
        </div>

        {login.isError && (
          <Alert tone="danger" title="Sign in failed">
            {getErrorMessage(login.error)}
          </Alert>
        )}

        <form className="stack" onSubmit={submit} noValidate>
          <TextField
            label="Username"
            name="username"
            autoComplete="username"
            required
            minLength={3}
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
          <TextField
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            minLength={6}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <Button
            type="submit"
            block
            loading={login.isPending}
            disabled={form.username.trim().length < 3 || form.password.length < 6}
          >
            Sign in
            {!login.isPending && <Icon name="arrowRight" size={16} />}
          </Button>
        </form>

        <div className="auth__divider">
          <span>New to ReturnRight?</span>
        </div>
        <Link to="/signup" className="btn btn--secondary btn--block">
          <Icon name="users" size={16} />
          Create a staff account
        </Link>

        {USE_MOCKS && (
          <aside className="demo-panel" aria-label="Demo accounts">
            <div className="demo-panel__head">
              <h2>Demo accounts</h2>
              <span className="muted">
                Password <code>{DEMO_PASSWORD}</code>
              </span>
            </div>
            <ul className="demo-list">
              {DEMO_STAFF.map((u) => (
                <li key={u.username}>
                  <button
                    type="button"
                    className="demo-list__item"
                    onClick={() => setForm({ username: u.username, password: DEMO_PASSWORD })}
                  >
                    <span className="demo-list__icon">
                      <Icon name={DEMO_ICON[u.role] ?? 'user'} size={16} />
                    </span>
                    <span className="demo-list__text">
                      <strong>{u.label}</strong>
                      <code>{u.username}</code>
                    </span>
                    <Icon name="chevronRight" size={16} className="demo-list__chevron" />
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}
      </section>
    </div>
  )
}
