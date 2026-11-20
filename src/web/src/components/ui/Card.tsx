import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Remove body padding, e.g. for an edge-to-edge table. */
  flush?: boolean
}

export function Card({ title, description, actions, children, className, flush }: CardProps) {
  return (
    <section className={['card', className].filter(Boolean).join(' ')} aria-label={title}>
      {(title || actions) && (
        <header className="card__header">
          <div>
            {title && <h2 className="card__title">{title}</h2>}
            {description && <p className="card__description">{description}</p>}
          </div>
          {actions && <div className="card__actions">{actions}</div>}
        </header>
      )}
      <div className={flush ? 'card__body card__body--flush' : 'card__body'}>{children}</div>
    </section>
  )
}
