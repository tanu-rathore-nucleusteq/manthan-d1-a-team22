import { getErrorMessage } from '../../api/errors'
import { Button } from './Button'

interface ErrorStateProps {
  title?: string
  message?: string
  error?: unknown
  onRetry?: () => void
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  error,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="state state--error" role="alert">
      <span className="state__icon" aria-hidden="true">
        !
      </span>
      <strong className="state__title">{title}</strong>
      <p>{message ?? getErrorMessage(error)}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
