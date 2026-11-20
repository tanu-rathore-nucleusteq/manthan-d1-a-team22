export type Theme = 'light' | 'dark'

/** Same key as the inline script in index.html, which applies the choice before first paint. */
const STORAGE_KEY = 'returnright.theme'

export function getStoredTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

export function getSystemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** Sets data-theme on <html>, which the tokens in styles.css follow, and remembers the choice. */
export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Storage blocked (private mode): the theme still applies for this page view.
  }
}
