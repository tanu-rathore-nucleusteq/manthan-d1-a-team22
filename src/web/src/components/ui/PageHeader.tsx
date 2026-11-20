import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Icon } from './Icon'

interface PageHeaderProps {
  title: string
  subtitle?: ReactNode
  actions?: ReactNode
  back?: { to: string; label: string }
  meta?: ReactNode
}

export function PageHeader({ title, subtitle, actions, back, meta }: PageHeaderProps) {
  return (
    <header className="page-header">
      {back && (
        <Link to={back.to} className="page-header__back">
          <Icon name="arrowLeft" size={15} />
          {back.label}
        </Link>
      )}
      <div className="page-header__row">
        <div className="page-header__text">
          <div className="page-header__title-row">
            <h1>{title}</h1>
            {meta}
          </div>
          {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="page-header__actions">{actions}</div>}
      </div>
    </header>
  )
}
