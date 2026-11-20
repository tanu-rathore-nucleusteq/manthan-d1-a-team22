import type { ReactNode } from 'react'

import type { Tone } from '../../lib/labels'
import { Icon, type IconName } from './Icon'

const ICON: Record<Tone, IconName> = {
  neutral: 'info',
  info: 'info',
  success: 'checkCircle',
  warning: 'alertTriangle',
  danger: 'alertCircle',
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
      <Icon name={ICON[tone]} size={20} className="alert__icon" />
      <div className="alert__content">
        {title && <strong className="alert__title">{title}</strong>}
        {children && <div className="alert__body">{children}</div>}
      </div>
      {actions && <div className="alert__actions">{actions}</div>}
    </div>
  )
}
