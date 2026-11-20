import { defineConfig, devices } from '@playwright/test'

// If `npx playwright install chromium` is blocked on the laptop, run with
// PW_CHANNEL=msedge (or chrome) to use the already-installed browser.
const channel = process.env.PW_CHANNEL
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'

export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], ...(channel && { channel }) },
    },
    {
      name: 'mobile',
      use: { ...devices['Pixel 7'], ...(channel && { channel }) },
    },
  ],
  // Starts the web app unless E2E_BASE_URL points at an already running stack (e.g. docker compose).
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: 'npm --prefix ../../src/web run dev',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
      },
})
