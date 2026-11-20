import { expect, test } from '@playwright/test'

test('customer lands on the return lookup page', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/returns$/)
  await expect(page.getByRole('heading', { name: 'Return an item' })).toBeVisible()
  await expect(page.getByLabel('Order number')).toBeVisible()
  await expect(page.getByLabel('Email')).toBeVisible()
})

test('staff pages redirect to sign in when logged out', async ({ page }) => {
  await page.goto('/finance')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Staff sign in' })).toBeVisible()
})

test('a staff role cannot open another role’s page', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('button', { name: /warehouse/i }).click()
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/warehouse$/)
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: 'Returns dashboard' })).toHaveCount(0)
  await expect(page.getByText("You don't have access to this page")).toBeVisible()
})
