import { expect, test } from '@playwright/test'

test('customer lands on start a return', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/returns$/)
  await expect(page.getByRole('heading', { name: 'Start a return' })).toBeVisible()
  await expect(page.getByLabel('Order number')).toBeVisible()
  await expect(page.getByLabel('Email')).toBeVisible()
})

test('staff pages redirect to sign in when logged out', async ({ page }) => {
  await page.goto('/finance')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Staff sign in' })).toBeVisible()
})
