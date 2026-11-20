import type { ReactNode } from 'react'

import type { Tone } from '../../lib/labels'

const ICON: Record<Tone, string> = {
  neutral: 'i',
  info: 'i',
  success: '✓',
  warning: '!',
  danger: '!',
}

interface AlertProps {
  tone?: Tone
  title?: string
  children?: ReactNode
  actions?: ReactNode
}

export function Alert({ tone = 'info', title, children, actions }: AlertProps) {
  return (
    <div className={`alert alert--${tone}`} role={tone === 'danger' ? 'alert' : 'status'}>
      <span className="alert__icon" aria-hidden="true">
        {ICON[tone]}
      </span>
      <div className="alert__content">
        {title && <strong className="alert__title">{title}</strong>}
        {children && <div className="alert__body">{children}</div>}
      </div>
      {actions && <div className="alert__actions">{actions}</div>}
    </div>
  )
}
