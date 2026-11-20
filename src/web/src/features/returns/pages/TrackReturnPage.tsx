import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { backend, USE_MOCKS } from '../../../api/backend'
import { getErrorMessage } from '../../../api/errors'
import { Alert } from '../../../components/ui/Alert'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { TextField } from '../../../components/ui/Field'
import { Icon } from '../../../components/ui/Icon'
import { returnKeys } from '../api'
import { saveProof } from '../customerProof'

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export function TrackReturnPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [email, setEmail] = useState('')
  const [errors, setErrors] = useState<{ code?: string; email?: string }>({})

  const track = useMutation({
    mutationFn: (input: { code: string; email: string }) =>
      backend.getReturn(input.code, { email: input.email }),
    onSuccess: (detail, input) => {
      saveProof(detail.return_code, input.email)
      queryClient.setQueryData(returnKeys.detail(detail.return_code), detail)
      navigate(`/returns/${detail.return_code}`)
    },
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const next = {
      code: /^RET-\d{3,}$/i.test(code.trim())
        ? undefined
        : 'Enter the return code from your label, e.g. RET-24051.',
      email: EMAIL.test(email.trim()) ? undefined : 'Enter a valid email address.',
    }
    setErrors(next)
    if (!next.code && !next.email) {
      track.mutate({ code: code.trim().toUpperCase(), email: email.trim().toLowerCase() })
    }
  }

  return (
    <div className="narrow narrow--centered">
      <span className="hero-icon">
        <Icon name="truck" size={26} />
      </span>
      <h1 className="display display--sm">Track a return</h1>
      <p className="lead">Enter your return code and the email you ordered with.</p>
      <Card className="card--raised">
        <form className="stack" onSubmit={submit} noValidate aria-label="Track a return">
          {track.isError && (
            <Alert tone="danger" title="Return not found">
              {getErrorMessage(track.error)}
            </Alert>
          )}
          <TextField
            label="Return code"
            placeholder="RET-24051"
            autoComplete="off"
            value={code}
            error={errors.code}
            onChange={(e) => setCode(e.target.value)}
          />
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            error={errors.email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Button type="submit" block loading={track.isPending}>
            {!track.isPending && <Icon name="search" size={16} />}
            Track return
          </Button>
        </form>
      </Card>
      {USE_MOCKS && (
        <p className="fine-print">
          Demo: try <code>RET-24051</code> with <code>priya.nair@example.com</code>.
        </p>
      )}
    </div>
  )
}
