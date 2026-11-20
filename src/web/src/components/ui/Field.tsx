import { useId, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'

interface FieldChrome {
  label: string
  hint?: string
  error?: string | null
}

function describedBy(id: string, hint?: string, error?: string | null) {
  return [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined
}

function FieldText({ id, hint, error }: { id: string; hint?: string; error?: string | null }) {
  return (
    <>
      {hint && (
        <span id={`${id}-hint`} className="field__hint">
          {hint}
        </span>
      )}
      {error && (
        <span id={`${id}-error`} className="field__error" role="alert">
          {error}
        </span>
      )}
    </>
  )
}

export function TextField({
  label,
  hint,
  error,
  className,
  ...input
}: FieldChrome & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  return (
    <div className={['field', className].filter(Boolean).join(' ')}>
      <label htmlFor={id} className="field__label">
        {label}
      </label>
      <input
        id={id}
        className="input"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        {...input}
      />
      <FieldText id={id} hint={hint} error={error} />
    </div>
  )
}

export function TextAreaField({
  label,
  hint,
  error,
  className,
  ...textarea
}: FieldChrome & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId()
  return (
    <div className={['field', className].filter(Boolean).join(' ')}>
      <label htmlFor={id} className="field__label">
        {label}
      </label>
      <textarea
        id={id}
        className="input input--textarea"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        {...textarea}
      />
      <FieldText id={id} hint={hint} error={error} />
    </div>
  )
}
