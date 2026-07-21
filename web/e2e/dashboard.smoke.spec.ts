import { expect, test } from '@playwright/test'

function parseRubValue(text: string): number {
  return Number(text.replace(/[^\d,-]/g, '').replace(',', '.'))
}

test('dashboard preview renders panels and reacts to transfer visibility', async ({ page }, testInfo) => {
  await page.goto('/', { waitUntil: 'networkidle' })

  await expect(page.getByRole('heading', { name: 'ОБЗОР' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'ПОСЛЕДНИЕ ТРАТЫ' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'ТРАТЫ ПО КАТЕГОРИЯМ' })).toBeVisible()
  await page.getByRole('button', { name: 'ВСЁ ВРЕМЯ' }).click()

  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath('dashboard-preview.png'),
  })

  const spentValue = page.getByTestId('overview-spent-value')
  const beforeText = (await spentValue.textContent()) ?? ''
  const beforeAmount = parseRubValue(beforeText)

  await page.getByTestId('hide-transfers-toggle').click()

  await expect
    .poll(async () => {
      const currentText = (await spentValue.textContent()) ?? ''
      return parseRubValue(currentText)
    })
    .toBeGreaterThan(beforeAmount)
})
