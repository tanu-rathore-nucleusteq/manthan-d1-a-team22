import type { ReactNode } from 'react'

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state">
      <span className="state__icon" aria-hidden="true">
        ∅
      </span>
      <strong className="state__title">{title}</strong>
      {children && <div className="state__body">{children}</div>}
    </div>
  )
}
