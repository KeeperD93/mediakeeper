// Daily digest window, a11y: it opens by itself over a portal page, with fictional
// content in every section, and passes a full axe pass in both of its views.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { openDigest } from './_fixtures/portal-daily-digest.js'

async function expectNoViolation(page) {
  const results = await new AxeBuilder({ page }).include('.dd-panel').analyze()
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
}

for (const compact of [false, true]) {
  test(`the daily digest passes axe in its ${compact ? 'compact' : 'full'} view`, async ({
    page,
  }) => {
    const tracker = await openDigest(page, compact)
    await expectNoViolation(page)
    expect(tracker.unexpected).toEqual([])
  })
}
