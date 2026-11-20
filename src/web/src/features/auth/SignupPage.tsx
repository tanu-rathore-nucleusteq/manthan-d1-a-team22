import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { ApiError, getErrorMessage } from '../../api/errors'
import { ROLES, type Role } from '../../auth/roles'
import { useToast } from '../../components/toast/toastContext'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { TextField } from '../../components/ui/Field'
import { Icon, type IconName } from '../../components/ui/Icon'
import { PASSWORD_HINT, passwordProblem } from '../../lib/password'
import { useCreateStaff } from '../team/api'

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

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

/**
 * Staff sign-up. The API has no self sign-up: POST /api/v1/staff creates an account and only
 * an operations manager may call it, so this page sits behind the manager role.
 */
export function SignupPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const create = useCreateStaff()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [role, setRole] = useState<Role | null>(null)
  const [errors, setErrors] = useState<Errors>({})

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const next: Errors = {
      fullName: fullName.trim().length >= 2 ? undefined : 'Enter their full name.',
      email: EMAIL.test(email.trim()) ? undefined : 'Enter a valid work email.',
      password: passwordProblem(password),
      confirm: confirm === password ? undefined : "The passwords don't match.",
      role: role ? undefined : 'Choose a role.',
    }
    setErrors(next)
    if (Object.values(next).some(Boolean)) return
    create.mutate(
      { full_name: fullName.trim(), email: email.trim().toLowerCase(), role: role!, password },
      {
        onSuccess: (member) => {
          toast({
            tone: 'success',
            title: 'Account created',
            body: `${member.full_name} can now sign in as ${member.username}.`,
          })
          navigate('/team')
        },
      },
    )
  }

  const loginTaken = create.error instanceof ApiError && create.error.status === 409

  return (
    <div className="auth">
      <section className="auth__panel" aria-labelledby="signup-panel-title">
        <span className="auth__badge">
          <Icon name="users" size={14} />
          Grow the team
        </span>
        <h2 id="signup-panel-title" className="auth__panel-title">
          Give a new team member their ReturnRight staff account.
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
            Create a staff account
          </h1>
          <p className="muted">
            Share the password with them in person. Manage everyone on the{' '}
            <Link to="/team">Team page</Link>.
          </p>
        </div>

        {create.isError && (
          <Alert tone="danger" title={loginTaken ? 'Login already in use' : 'Account not created'}>
            {getErrorMessage(create.error)}
          </Alert>
        )}

        <form className="stack" onSubmit={submit} noValidate>
          <TextField
            label="Full name"
            name="fullName"
            autoComplete="off"
            value={fullName}
            error={errors.fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <TextField
            label="Work email"
            name="email"
            type="email"
            autoComplete="off"
            placeholder="name@company.com"
            hint="They sign in with this email or the part before the @."
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
              hint={PASSWORD_HINT}
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

          <Button type="submit" block loading={create.isPending}>
            Create account
            {!create.isPending && <Icon name="arrowRight" size={16} />}
          </Button>
        </form>
      </section>
    </div>
  )
}
