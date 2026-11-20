import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'

import { backend } from '../../api/backend'
import { ApiError, getErrorMessage } from '../../api/errors'
import type { SignupRequest } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { HOME_BY_ROLE, ROLES, type Role } from '../../auth/roles'
import { useToast } from '../../components/toast/toastContext'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { TextField } from '../../components/ui/Field'
import { Icon, type IconName } from '../../components/ui/Icon'

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const MIN_PASSWORD = 8

const ROLE_OPTIONS: { value: Role; label: string; hint: string; icon: IconName }[] = [
  {
    value: ROLES.warehouseAgent,
    label: 'Warehouse agent',
    hint: 'Receive parcels, grade items and settle refunds.',
    icon: 'clipboardCheck',
  },
  {
    value: ROLES.financeReviewer,
    label: 'Finance reviewer',
    hint: 'Approve refunds above ₹10,000 and keep the ledger.',
    icon: 'shieldCheck',
  },
  {
    value: ROLES.operationsManager,
    label: 'Operations manager',
    hint: 'Track return rates, reasons and flagged customers.',
    icon: 'barChart',
  },
]

type Errors = Partial<Record<'fullName' | 'email' | 'password' | 'confirm' | 'role', string>>

export function SignupPage() {
  const { session, signIn } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [role, setRole] = useState<Role | null>(null)
  const [errors, setErrors] = useState<Errors>({})

  // Create the account, then sign in with the same details so the user lands on their queue.
  const signup = useMutation({
    mutationFn: async (body: SignupRequest) => {
      await backend.signup(body)
      return backend.login({ username: body.email, password: body.password })
    },
    onSuccess: (token, body) => {
      signIn({ token: token.access_token, role: token.role, name: body.full_name })
      toast({ tone: 'success', title: 'Account created', body: `Welcome, ${body.full_name}.` })
      navigate(HOME_BY_ROLE[token.role], { replace: true })
    },
  })

  if (session && !signup.isPending) return <Navigate to={HOME_BY_ROLE[session.role]} replace />

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const next: Errors = {
      fullName: fullName.trim().length >= 2 ? undefined : 'Enter your full name.',
      email: EMAIL.test(email.trim()) ? undefined : 'Enter a valid work email.',
      password:
        password.length >= MIN_PASSWORD ? undefined : `Use at least ${MIN_PASSWORD} characters.`,
      confirm: confirm === password ? undefined : "The passwords don't match.",
      role: role ? undefined : 'Choose a role.',
    }
    setErrors(next)
    if (Object.values(next).some(Boolean)) return
    signup.mutate({
      full_name: fullName.trim(),
      email: email.trim().toLowerCase(),
      password,
      role: role!,
    })
  }

  const emailTaken = signup.error instanceof ApiError && signup.error.status === 409

  return (
    <div className="auth">
      <section className="auth__panel" aria-labelledby="signup-panel-title">
        <span className="auth__badge">
          <Icon name="users" size={14} />
          Join the team
        </span>
        <h2 id="signup-panel-title" className="auth__panel-title">
          Set up your ReturnRight staff account in a minute.
        </h2>
        <ul className="auth__features">
          {ROLE_OPTIONS.map((r) => (
            <li key={r.value}>
              <span className="auth__feature-icon">
                <Icon name={r.icon} size={18} />
              </span>
              <span>
                <strong>{r.label}</strong>
                <span>{r.hint}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="auth__form" aria-labelledby="signup-title">
        <div className="auth__form-head">
          <h1 id="signup-title" className="auth__title">
            Create your account
          </h1>
          <p className="muted">
            Already have one? <Link to="/login">Sign in</Link>
          </p>
        </div>

        {signup.isError && (
          <Alert tone="danger" title={emailTaken ? 'Email already registered' : 'Sign up failed'}>
            {getErrorMessage(signup.error)}
          </Alert>
        )}

        <form className="stack" onSubmit={submit} noValidate>
          <TextField
            label="Full name"
            name="fullName"
            autoComplete="name"
            value={fullName}
            error={errors.fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <TextField
            label="Work email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            hint="You'll sign in with this email or the part before the @."
            value={email}
            error={errors.email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <div className="grid-2">
            <TextField
              label="Password"
              name="password"
              type="password"
              autoComplete="new-password"
              hint={`At least ${MIN_PASSWORD} characters.`}
              value={password}
              error={errors.password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <TextField
              label="Confirm password"
              name="confirm"
              type="password"
              autoComplete="new-password"
              value={confirm}
              error={errors.confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>

          <fieldset
            className="role-picker"
            aria-describedby={errors.role ? 'role-error' : undefined}
          >
            <legend className="field__label">Role</legend>
            <div className="role-picker__options">
              {ROLE_OPTIONS.map((r) => (
                <label key={r.value} className="role-option">
                  <input
                    type="radio"
                    name="role"
                    value={r.value}
                    checked={role === r.value}
                    onChange={() => {
                      setRole(r.value)
                      setErrors((x) => ({ ...x, role: undefined }))
                    }}
                  />
                  <span className="role-option__icon">
                    <Icon name={r.icon} size={18} />
                  </span>
                  <span className="role-option__text">
                    <strong>{r.label}</strong>
                    <span>{r.hint}</span>
                  </span>
                </label>
              ))}
            </div>
            {errors.role && (
              <span id="role-error" className="field__error" role="alert">
                {errors.role}
              </span>
            )}
          </fieldset>

          <Button type="submit" block loading={signup.isPending}>
            Create account
            {!signup.isPending && <Icon name="arrowRight" size={16} />}
          </Button>
        </form>
      </section>
    </div>
  )
}
