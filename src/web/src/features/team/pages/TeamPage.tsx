import { useState, type FormEvent } from 'react'

import { getErrorMessage } from '../../../api/errors'
import type { StaffMemberResponse } from '../../../api/types'
import { ROLE_LABEL, ROLES, type Role } from '../../../auth/roles'
import { useToast } from '../../../components/toast/toastContext'
import { Alert } from '../../../components/ui/Alert'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { ErrorState } from '../../../components/ui/ErrorState'
import { TextField } from '../../../components/ui/Field'
import { LoadingState } from '../../../components/ui/LoadingState'
import { PageHeader } from '../../../components/ui/PageHeader'
import { Segmented } from '../../../components/ui/Segmented'
import { useCreateStaff, useSetStaffActive, useStaff } from '../api'

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

const ROLE_OPTIONS = Object.values(ROLES).map((role) => ({ value: role, label: ROLE_LABEL[role] }))

interface Errors {
  fullName?: string
  email?: string
  role?: string
  password?: string
}

/** Same rule as the API: at least 10 characters with a letter and a number. */
function passwordProblem(password: string): string | undefined {
  if (password.length < 10) return 'Use at least 10 characters.'
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
    return 'Use at least one letter and one number.'
  return undefined
}

export function TeamPage() {
  const staff = useStaff()

  return (
    <>
      <PageHeader
        title="Team"
        subtitle="Staff accounts. There is no self sign-up: add each person here with a temporary password."
      />
      <div className="grid-2 grid-2--top">
        <AddStaffCard />
        <Card title="Staff accounts" description="Switched-off accounts can't sign in." flush>
          {staff.isPending ? (
            <LoadingState label="Loading staff" lines={4} />
          ) : staff.isError ? (
            <ErrorState error={staff.error} onRetry={() => staff.refetch()} />
          ) : (
            <StaffTable members={staff.data} />
          )}
        </Card>
      </div>
    </>
  )
}

function AddStaffCard() {
  const create = useCreateStaff()
  const toast = useToast()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<Role | null>(null)
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Errors>({})

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const next: Errors = {
      fullName: fullName.trim().length >= 2 ? undefined : 'Enter their full name.',
      email: EMAIL.test(email.trim()) ? undefined : 'Enter a valid work email.',
      role: role ? undefined : 'Choose a role.',
      password: passwordProblem(password),
    }
    setErrors(next)
    if (Object.values(next).some(Boolean)) return
    create.mutate(
      { full_name: fullName.trim(), email: email.trim(), role: role!, password },
      {
        onSuccess: (member) => {
          toast({
            tone: 'success',
            title: `${member.full_name} can now sign in as ${member.username}`,
          })
          setFullName('')
          setEmail('')
          setRole(null)
          setPassword('')
        },
      },
    )
  }

  return (
    <Card
      title="Add a staff member"
      description="Share the temporary password with them in person."
    >
      <form onSubmit={submit} noValidate aria-label="Add a staff member">
        <TextField
          label="Full name"
          autoComplete="off"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          error={errors.fullName}
        />
        <TextField
          label="Work email"
          type="email"
          autoComplete="off"
          hint="They sign in with this email or the part before the @."
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.email}
        />
        <Segmented<Role> legend="Role" options={ROLE_OPTIONS} value={role} onChange={setRole} />
        {errors.role && (
          <span className="field__error" role="alert">
            {errors.role}
          </span>
        )}
        <TextField
          label="Temporary password"
          type="password"
          autoComplete="new-password"
          hint="At least 10 characters, with a letter and a number."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
        />
        {create.isError && (
          <Alert tone="danger" title="Couldn't add this staff member">
            {getErrorMessage(create.error)}
          </Alert>
        )}
        <div className="form-actions">
          <Button type="submit" loading={create.isPending}>
            Add staff member
          </Button>
        </div>
      </form>
    </Card>
  )
}

function StaffTable({ members }: { members: StaffMemberResponse[] }) {
  const setActive = useSetStaffActive()
  const toast = useToast()

  const toggle = (member: StaffMemberResponse) =>
    setActive.mutate(
      { staffId: member.user_id, isActive: !member.is_active },
      {
        onSuccess: (updated) =>
          toast({
            tone: 'success',
            title: `${updated.full_name} ${updated.is_active ? 'can sign in again' : 'can no longer sign in'}`,
          }),
        onError: (error) => toast({ tone: 'danger', title: getErrorMessage(error) }),
      },
    )

  return (
    <div className="table-wrap">
      <table className="table">
        <caption className="visually-hidden">Staff accounts</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Sign-in</th>
            <th scope="col">Role</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="visually-hidden">Action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.user_id}>
              <td>{member.full_name}</td>
              <td className="mono">{member.username}</td>
              <td>{ROLE_LABEL[member.role]}</td>
              <td>
                <Badge tone={member.is_active ? 'success' : 'neutral'}>
                  {member.is_active ? 'Active' : 'Switched off'}
                </Badge>
              </td>
              <td>
                <Button
                  size="sm"
                  variant={member.is_active ? 'ghost' : 'secondary'}
                  disabled={setActive.isPending}
                  onClick={() => toggle(member)}
                  aria-label={`${member.is_active ? 'Switch off' : 'Switch on'} ${member.full_name}`}
                >
                  {member.is_active ? 'Switch off' : 'Switch on'}
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
