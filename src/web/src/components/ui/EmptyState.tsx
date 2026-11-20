import type { ReactNode } from 'react'

import { Icon, type IconName } from './Icon'

export function EmptyState({
  title,
  icon = 'inbox',
  children,
}: {
  title: string
  icon?: IconName
  children?: ReactNode
}) {
  return (
    <div className="state">
      <span className="state__icon">
        <Icon name={icon} size={22} />
      </span>
      <strong className="state__title">{title}</strong>
      {children && <div className="state__body">{children}</div>}
    </div>
  )
}
