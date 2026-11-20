import { useCallback, useState, type ReactNode } from 'react'

import { Icon, type IconName } from '../ui/Icon'
import { ToastContext, type ToastInput } from './toastContext'

interface Toast extends ToastInput {
  id: number
}

const TOAST_ICON: Record<string, IconName> = {
  success: 'checkCircle',
  danger: 'alertCircle',
  warning: 'alertTriangle',
}

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback(
    (id: number) => setToasts((all) => all.filter((t) => t.id !== id)),
    [],
  )

  const push = useCallback(
    (toast: ToastInput) => {
      const id = nextId++
      setToasts((all) => [...all, { ...toast, id }])
      setTimeout(() => dismiss(id), 5000)
    },
    [dismiss],
  )

  return (
    <ToastContext value={push}>
      {children}
      <div className="toasts" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => {
          const tone = t.tone ?? 'info'
          return (
            <div key={t.id} className={`toast toast--${tone}`} role="status">
              <Icon name={TOAST_ICON[tone] ?? 'info'} size={20} className="toast__icon" />
              <div className="toast__content">
                <strong>{t.title}</strong>
                {t.body && <p>{t.body}</p>}
              </div>
              <button
                type="button"
                className="icon-btn icon-btn--sm"
                onClick={() => dismiss(t.id)}
                aria-label="Dismiss"
              >
                <Icon name="x" size={16} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext>
  )
}
