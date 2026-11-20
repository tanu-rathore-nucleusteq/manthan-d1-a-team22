import type { Tone } from '../../lib/labels'
import { Icon, type IconName } from './Icon'

interface StatTileProps {
  label: string
  value: string
  hint?: string
  icon?: IconName
  /** Colours the icon chip; the value itself always stays neutral. */
  tone?: Tone | 'accent'
}

export function StatTile({ label, value, hint, icon, tone = 'accent' }: StatTileProps) {
  return (
    <div className="stat">
      <div className="stat__top">
        <span className="stat__label">{label}</span>
        {icon && (
          <span className={`stat__icon stat__icon--${tone}`}>
            <Icon name={icon} size={18} />
          </span>
        )}
      </div>
      <span className="stat__value">{value}</span>
      {hint && <span className="stat__hint">{hint}</span>}
    </div>
  )
}
