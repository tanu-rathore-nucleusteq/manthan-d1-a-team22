import { useState, type FormEvent, type ReactNode } from 'react'

import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { TextField } from '../../../components/ui/Field'
import { getProof, saveProof } from '../customerProof'

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

/** Asks for the order email when this tab has no proof for the return yet. */
export function ProofGate({
  returnCode,
  children,
}: {
  returnCode: string
  children: (email: string) => ReactNode
}) {
  const [email, setEmail] = useState(() => getProof(returnCode))
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)

  if (email) return children(email)

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!EMAIL.test(draft.trim()))
      return setError('Enter the email address you used for the order.')
    saveProof(returnCode, draft)
    setEmail(draft.trim().toLowerCase())
  }

  return (
    <div className="narrow">
      <Card
        title={`Return ${returnCode.toUpperCase()}`}
        description="Confirm it's you to see this return."
      >
        <form className="stack" onSubmit={submit} noValidate>
          <TextField
            label="Order email"
            type="email"
            autoComplete="email"
            value={draft}
            error={error}
            onChange={(e) => setDraft(e.target.value)}
          />
          <Button type="submit">Continue</Button>
        </form>
      </Card>
    </div>
  )
}
