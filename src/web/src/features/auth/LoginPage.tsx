import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
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
    <div className="auth-page">
      <div className="auth-card card">
        <div className="card__body">
          <h1 className="auth-card__title">Staff sign in</h1>
          <p className="muted">Warehouse, finance and operations staff.</p>

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
            </Button>
          </form>
        </div>
      </div>

      {USE_MOCKS && (
        <aside className="demo-panel" aria-label="Demo accounts">
          <h2>Demo accounts</h2>
          <p className="muted">
            Password for all: <code>{DEMO_PASSWORD}</code>
          </p>
          <ul className="demo-list">
            {DEMO_STAFF.map((u) => (
              <li key={u.username}>
                <button
                  type="button"
                  className="demo-list__item"
                  onClick={() => setForm({ username: u.username, password: DEMO_PASSWORD })}
                >
                  <code>{u.username}</code>
                  <span>{u.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>
      )}
    </div>
  )
}
