import { expect, test } from '@playwright/test'

// 1x1 transparent PNG, so the film card never reaches the network
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64',
)

test('the app loads, filters, brushes, pins and restores from the hash', async ({ page, browser }) => {
  const errors: string[] = []
  const stub = (p: typeof page) =>
    p.route('https://image.tmdb.org/**', (route) => route.fulfill({ contentType: 'image/png', body: PNG }))
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  page.on('pageerror', (err) => errors.push(err.message))
  await stub(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')

  await expect(page.getByRole('tab', { name: 'Taste by country' })).toHaveAttribute('aria-selected', 'true')
  for (const area of ['a', 'b', 'e']) {
    await expect(page.locator(`.area-${area}`)).toBeVisible()
  }
  await expect(page.locator('.area-c')).toHaveCount(0)

  await page.getByRole('radio', { name: 'Horror' }).click()
  await expect(page.locator('.area-a')).toContainText(/share of horror/i)

  await page.getByRole('button', { name: 'Zoom in' }).click()
  await expect(page.getByRole('button', { name: 'reset view' })).toBeVisible()

  // a click inside the brushed years picks the genre under it and keeps the years
  const years = page.locator('.area-b .tl-brush .overlay')
  const yb = await years.boundingBox()
  if (!yb) throw new Error('timeline overlay has no box')
  await page.mouse.click(yb.x + yb.width * 0.85, yb.y + yb.height * 0.97)
  await expect(page.getByRole('radio', { name: 'Action & Adventure' })).toHaveAttribute('aria-checked', 'true')
  await expect(page.getByLabel('From year')).toHaveValue('1990')

  await page.getByRole('tab', { name: 'Money & ratings' }).click()
  await expect(page.locator('.area-c canvas')).toHaveCount(1)
  for (const area of ['e', 'g']) {
    await expect(page.locator(`.area-${area}`)).toBeVisible()
  }
  const card = page.locator('.area-g')

  const overlay = page.locator('.area-c .overlay')
  await expect(overlay).toBeVisible()
  const box = await overlay.boundingBox()
  if (!box) throw new Error('scatter overlay has no box')
  await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.3)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5, { steps: 10 })
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.7, { steps: 10 })
  await page.mouse.up()
  await expect(page.locator('.area-e .panel-note')).toContainText('inside the brush')

  await expect(page.getByRole('button', { name: 'Remove scatter brush' })).toBeVisible()

  await page.locator('.area-e [role="row"]').nth(1).click()
  await expect(card).not.toContainText('Hover a dot or a row to see a film')
  const title = (await card.locator('h3').innerText()).trim()
  expect(title).not.toBe('')
  await expect(page).toHaveURL(/film=tt/)
  await expect(page).toHaveURL(/tab=ratings/)

  await page.getByRole('tab', { name: 'Franchises' }).click()
  for (const area of ['d', 'c', 'g']) {
    await expect(page.locator(`.area-${area}`)).toBeVisible()
  }

  await expect(page).toHaveURL(/tab=franchises/)

  const page2 = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await stub(page2)
  await page2.goto(page.url())
  await expect(page2.getByRole('tab', { name: 'Franchises' })).toHaveAttribute('aria-selected', 'true')
  await expect(page2.locator('.area-g h3')).toHaveText(title)
  await page2.close()

  expect(errors).toEqual([])
})
