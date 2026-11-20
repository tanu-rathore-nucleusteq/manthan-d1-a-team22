import { expect, test, type Page } from '@playwright/test'

async function signIn(page: Page, username: 'warehouse' | 'finance' | 'manager') {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill('demo1234')
  await page.getByRole('button', { name: 'Sign in' }).click()
  // Wait for the login to finish before navigating, or the session is never stored.
  await expect(page).not.toHaveURL(/\/login$/)
}

test('wrong password is refused', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill('finance')
  await page.getByLabel('Password').fill('wrong-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Sign in failed' })).toBeVisible()
})

test('warehouse agent grades a high-value return and it goes to finance', async ({ page }) => {
  await signIn(page, 'warehouse')
  await page.getByLabel('Scan or enter return code').fill('ret-24054')
  await page.getByRole('button', { name: 'Open return' }).click()
  await expect(page.getByRole('heading', { name: 'RET-24054' })).toBeVisible()

  await page.getByRole('button', { name: 'Submit inspection' }).click()
  await expect(page.getByText('Choose a grade and a decision.')).toBeVisible()

  await page.getByRole('button', { name: /Quick fill/ }).click()
  await expect(page.getByText('Needs finance approval')).toBeVisible()
  await page.getByRole('button', { name: 'Submit inspection' }).click()
  await expect(page.getByText(/sent for finance approval/)).toBeVisible()
})

test('warehouse agent grades C and the refund is halved', async ({ page }) => {
  await signIn(page, 'warehouse')
  await page.goto('/warehouse/returns/RET-24055')
  await page.getByLabel('C', { exact: true }).check()
  await page.getByLabel('Accept').check()
  await expect(page.locator('.inspect-item__refund')).toHaveText('₹1,099.50')
  await page.getByRole('button', { name: 'Submit inspection' }).click()
  await expect(page.getByText('Refund of ₹1,099.50 paid')).toBeVisible()
})

test('finance approves a refund once; it lands in the ledger', async ({ page }) => {
  await signIn(page, 'finance')
  await expect(page.getByRole('heading', { name: 'Refund approvals' })).toBeVisible()
  await page.getByRole('link', { name: 'RET-24056' }).first().click()
  await page.getByRole('button', { name: 'Approve refund' }).click()
  await page.getByRole('button', { name: 'Approve and pay' }).click()
  await expect(page.getByText('Refund for RET-24056 approved and paid')).toBeVisible()
  await expect(page.getByRole('link', { name: 'RET-24056' })).toHaveCount(0)

  await page.getByRole('link', { name: 'Ledger' }).click()
  await expect(page.getByRole('cell', { name: '₹14,999' })).toBeVisible()
})

test('rejecting a refund requires a reason', async ({ page }) => {
  await signIn(page, 'finance')
  await page.goto('/finance/returns/RET-24057')
  await expect(page.getByText('Flagged customer').first()).toBeVisible()
  await page.getByRole('button', { name: 'Reject', exact: true }).click()
  const confirm = page.getByRole('button', { name: 'Reject refund' })
  await expect(confirm).toBeDisabled()
  await page.getByLabel(/Reason for rejecting/).fill('Photo shows heavy use')
  await confirm.click()
  await expect(page.getByText('Refund for RET-24057 rejected')).toBeVisible()
})

test('manager sees the dashboard with a table view for each chart', async ({ page }) => {
  await signIn(page, 'manager')
  await expect(page.getByRole('heading', { name: 'Returns dashboard' })).toBeVisible()
  await expect(page.getByRole('list', { name: 'Return rate' })).toContainText('Apparel')
  await expect(page.getByRole('cell', { name: 'Ananya Das' })).toBeVisible()
  await page.getByRole('button', { name: 'Show table' }).first().click()
  await expect(page.getByRole('columnheader', { name: 'Return rate' })).toBeVisible()
})
