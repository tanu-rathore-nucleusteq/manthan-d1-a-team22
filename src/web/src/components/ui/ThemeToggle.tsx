import { useState } from 'react'

import { applyTheme, getStoredTheme, getSystemTheme, type Theme } from '../../lib/theme'
import { Icon } from './Icon'

/** Switches between light and dark. Starts from the saved choice, else the system setting. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme() ?? getSystemTheme())
  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  const label = `Switch to ${next} mode`

  return (
    <button
      type="button"
      className="icon-btn theme-toggle"
      aria-label={label}
      title={label}
      onClick={() => {
        applyTheme(next)
        setTheme(next)
      }}
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
    </button>
  )
}
