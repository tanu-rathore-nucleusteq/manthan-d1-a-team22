import { expect, test } from '@playwright/test'

// Runs against the web app's mock backend (synthetic demo data). Each test gets a fresh tab, so a fresh seed.

const PHOTO = {
  name: 'kurta.png',
  mimeType: 'image/png',
  // 1x1 transparent PNG
  buffer: Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
    'base64',
  ),
}

async function findOrder(page: import('@playwright/test').Page, order: string, email: string) {
  await page.goto('/returns')
  await page.getByLabel('Order number').fill(order)
  await page.getByLabel('Email').fill(email)
  await page.getByRole('button', { name: 'Find order' }).click()
}

test('electronics on day 11 is refused with its reason', async ({ page }) => {
  await findOrder(page, 'RR-10021', 'asha.verma@example.com')
  const headphones = page.getByRole('listitem').filter({ hasText: 'Wireless headphones' })
  await expect(headphones.getByRole('checkbox')).toBeDisabled()
  await expect(headphones).toContainText('Not returnable')
  await expect(headphones).toContainText('day 11')
  const briefs = page.getByRole('listitem').filter({ hasText: 'Cotton briefs' })
  await expect(briefs).toContainText('cannot be returned')
})

test('unknown order shows a clear error', async ({ page }) => {
  await findOrder(page, 'RR-99999', 'nobody@example.com')
  await expect(page.getByRole('alert').filter({ hasText: 'Order not found' })).toBeVisible()
})

test('customer creates a return, gets a label and marks it shipped', async ({ page }) => {
  await findOrder(page, 'RR-10021', 'asha.verma@example.com')

  // Items
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByText('Select at least one item to return.')).toBeVisible()
  await page.getByRole('listitem').filter({ hasText: 'Cotton kurta' }).getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Continue' }).click()

  // Reason
  await page.getByLabel('Size or fit').check()
  await page.getByRole('button', { name: 'Continue' }).click()

  // Photo
  await page.locator('input[type="file"]').setInputFiles(PHOTO)
  await expect(page.getByAltText('Selected item')).toBeVisible()
  await page.getByRole('button', { name: 'Continue' }).click()

  // Refund method
  await page.getByLabel(/Store credit/).check()
  await page.getByRole('button', { name: 'Continue' }).click()

  // Review and submit
  await expect(page.getByRole('heading', { name: 'Review your return' })).toBeVisible()
  await page.getByRole('button', { name: 'Submit return' }).click()

  await expect(page.getByRole('heading', { name: 'Your return label' })).toBeVisible()
  await expect(page.getByText('Return created')).toBeVisible()
  await expect(page.getByRole('img', { name: /QR code for return RET-/ })).toBeVisible()

  await page.getByRole('button', { name: "I've shipped it" }).click()
  await expect(page).toHaveURL(/\/returns\/RET-\d+$/)
  await expect(page.getByText('Your parcel is on its way')).toBeVisible()
})

test('customer tracks an existing return', async ({ page }) => {
  await page.goto('/returns/track')
  await page.getByLabel('Return code').fill('RET-24051')
  await page.getByLabel('Email').fill('priya.nair@example.com')
  await page.getByRole('button', { name: 'Track return' }).click()
  await expect(page.getByRole('heading', { name: 'Return RET-24051' })).toBeVisible()
  await expect(page.getByLabel('Return status history')).toContainText('In transit')
})
