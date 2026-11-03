// Layout of the period controls of "My profile": the menu in a narrow card, the four tabs
// on one line in a wider one, and what a finger gets on a phone.

import { test, expect } from '@playwright/test'
import { card, LABELS, menu, openProfile, tab } from './_fixtures/portal-profile-ranking.js'

const tabs = page => card(page).locator('[role="tab"]')

// The title and the menu on one row, inside the card, side by side.
async function expectMenu(page) {
  await expect(menu(page)).toBeVisible()
  await expect(tabs(page).first()).toBeHidden()
  const facts = await card(page).evaluate(box => {
    const rect = selector => box.querySelector(selector).getBoundingClientRect()
    const select = rect('select')
    const title = rect('.gc-box-title')
    return {
      space: select.left - title.right,
      inside: box.getBoundingClientRect().right - select.right,
      sameRow: title.top < select.bottom && select.top < title.bottom,
    }
  })
  expect(facts.space).toBeGreaterThanOrEqual(0)
  expect(facts.inside).toBeGreaterThan(0)
  expect(facts.sameRow).toBe(true)
}

// The four tabs on one line, inside the card, whichever is on: the active one is bolder.
async function expectTabs(page) {
  await expect(menu(page)).toBeHidden()
  await expect(tabs(page)).toHaveCount(4)
  for (let index = 0; index < 4; index += 1) {
    await tabs(page).nth(index).click()
    await expect(tabs(page).nth(index)).toHaveAttribute('aria-selected', 'true')
    const facts = await tabs(page).evaluateAll(items => {
      const box = items[0].closest('.gc-lb-box').getBoundingClientRect()
      const rects = items.map(item => item.getBoundingClientRect())
      return {
        lines: new Set(rects.map(rect => Math.round(rect.top))).size,
        inside: box.right - Math.max(...rects.map(rect => rect.right)),
        clipped: items.filter(item => item.scrollWidth > item.clientWidth).length,
      }
    })
    expect(facts.lines).toBe(1)
    expect(facts.inside).toBeGreaterThan(0)
    expect(facts.clipped).toBe(0)
  }
}

test.describe('On a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  for (const width of [1280, 1366, 1600]) {
    for (const locale of ['fr', 'en']) {
      test(`at ${width}px in ${locale}, a card this narrow gets the menu`, async ({ page }) => {
        await openProfile(page, { width, locale })
        await expectMenu(page)
        await expect(menu(page)).toHaveCSS('min-height', '0px')
      })
    }
  }

  for (const width of [1024, 1680, 1920]) {
    test(`at ${width}px, a card this wide gets the tabs`, async ({ page }) => {
      await openProfile(page, { width })
      await expectTabs(page)
    })
  }

  test('the menu keeps the surface and the arrow of the menus of the portal', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    const look = await menu(page).evaluate(select => {
      const style = getComputedStyle(select)
      const probe = document.createElement('i')
      document.body.append(probe)
      const read = token => {
        probe.style.backgroundColor = `var(${token})`
        return getComputedStyle(probe).backgroundColor
      }
      const facts = {
        arrow: style.backgroundImage.includes('svg'),
        top: style.paddingTop,
        border: style.borderTopWidth,
        left: style.paddingLeft,
        right: style.paddingRight,
        radius: style.borderTopLeftRadius,
        surface: style.backgroundColor === read('--portal-surface-3'),
        text: style.color === read('--portal-text-primary'),
        // The neutral grey of the page, not the blue of the portal's panels.
        list: getComputedStyle(select.options[0]).backgroundColor === read('--portal-bg-primary'),
        compact: select.getBoundingClientRect().height < 28,
      }
      probe.remove()
      return facts
    })
    expect(look).toEqual({
      arrow: true,
      top: '4px',
      border: '1px',
      left: '12px',
      right: '28px',
      radius: '14px',
      surface: true,
      text: true,
      list: true,
      compact: true,
    })
  })

  test('the menu is as wide as the word shown, and its right edge stays', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    const month = await menu(page).boundingBox()
    await menu(page).selectOption('today')
    await expect(menu(page)).toHaveValue('today')
    const today = await menu(page).boundingBox()
    expect(month.width).toBeLessThan(today.width)
    expect(Math.round(month.x + month.width)).toBe(Math.round(today.x + today.width))
  })

  test('the keyboard shows where it is on the menu', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    await card(page).locator('.gc-box-title').focus()
    await page.keyboard.press('Tab')
    await expect(menu(page)).toBeFocused()
    await expect(menu(page)).toHaveCSS('outline-style', 'solid')
    await expect(menu(page)).toHaveCSS('outline-offset', '2px')
  })

  test('a card its neighbours stretch keeps the rows under the title', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    const gap = () =>
      card(page).evaluate(box => {
        const select = box.querySelector('select').getBoundingClientRect()
        return box.querySelector('.gc-lb-row').getBoundingClientRect().top - select.bottom
      })
    const before = await gap()
    const { height } = await card(page).boundingBox()
    await card(page).evaluate((box, target) => {
      box.style.minHeight = `${target}px`
    }, height + 400)
    expect((await card(page).boundingBox()).height).toBeGreaterThan(height + 399)
    expect(await gap()).toBe(before)
  })

  test('the tabs keep their margins, their border and their gaps', async ({ page }) => {
    await openProfile(page, { width: 1920 })
    const facts = await tab(page, 'week').evaluate(item => {
      const style = getComputedStyle(item)
      const row = getComputedStyle(item.parentElement)
      const box = getComputedStyle(item.closest('.gc-lb-box'))
      return {
        top: style.paddingTop,
        inline: parseFloat(style.paddingLeft),
        border: style.borderTopWidth,
        rowGap: row.rowGap,
        columnGap: parseFloat(row.columnGap),
        cardGap: box.rowGap,
      }
    })
    expect(facts).toEqual({
      top: '6px',
      inline: expect.any(Number),
      border: '1px',
      rowGap: '14px',
      columnGap: expect.any(Number),
      cardGap: '8px',
    })
    // In a card this wide, the margin and the gap sit between their two tokens.
    expect(facts.inline).toBeGreaterThan(6)
    expect(facts.inline).toBeLessThanOrEqual(14)
    expect(facts.columnGap).toBeGreaterThanOrEqual(4)
    expect(facts.columnGap).toBeLessThanOrEqual(8)
  })
})

test.describe('On a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone')

  for (const width of [320, 360, 375]) {
    test(`at ${width}px, the menu keeps a height of 44 px`, async ({ page }) => {
      await openProfile(page, { width })
      await expectMenu(page)
      const box = await menu(page).boundingBox()
      expect(box.height).toBeGreaterThanOrEqual(44)
    })
  }

  for (const width of [376, 390, 430]) {
    for (const locale of ['fr', 'en']) {
      test(`at ${width}px in ${locale}, the four tabs hold on one line`, async ({ page }) => {
        await openProfile(page, { width, locale })
        await expectTabs(page)
      })
    }
  }

  test('a finger gets 44 px on each tab, and the tabs win over the title', async ({ page }) => {
    await openProfile(page, { width: 376 })
    const week = tab(page, 'week')
    await week.scrollIntoViewIfNeeded()
    const box = await week.boundingBox()
    const hit = (x, y) =>
      page.evaluate(
        ([left, top]) => document.elementFromPoint(left, top)?.closest('a, button')?.textContent,
        [x, y],
      )
    const x = box.x + box.width / 2
    const y = box.y + box.height / 2
    expect((await hit(x, y + 20)).trim()).toBe(LABELS.week)
    expect((await hit(x, y - 20)).trim()).toBe(LABELS.week)

    const today = await tab(page, 'today').boundingBox()
    const title = await card(page).locator('.gc-box-title').boundingBox()
    const left = today.x + Math.min(today.width, title.width) / 2
    const titleCenter = title.y + title.height / 2
    // The band of the tab reaches under the title: where they meet, the tab gets the finger.
    expect((await hit(left, titleCenter + 12)).trim()).toBe(LABELS.today)
    expect((await hit(left, titleCenter)).trim()).toContain('Classement')
    expect((await hit(left, titleCenter - 20)).trim()).toContain('Classement')
  })

  test('a finger gets 44 px on the title next to the menu', async ({ page }) => {
    await openProfile(page, { width: 375 })
    const title = card(page).locator('.gc-box-title')
    await title.scrollIntoViewIfNeeded()
    const box = await title.boundingBox()
    const hit = offset =>
      page.evaluate(
        ([left, top]) => document.elementFromPoint(left, top)?.closest('a')?.textContent,
        [box.x + box.width / 2, box.y + box.height / 2 + offset],
      )
    expect((await hit(20)).trim()).toContain('Classement')
    expect((await hit(-20)).trim()).toContain('Classement')
  })

  test('the card stays inside the screen with the menu', async ({ page }) => {
    await openProfile(page, { width: 320 })
    const box = await card(page).boundingBox()
    expect(box.x + box.width).toBeLessThanOrEqual(320)
  })
})
