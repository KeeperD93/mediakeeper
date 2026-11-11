// Metal frame of the first three places: each has its metal, a slow light turns around the
// frame, nothing shines around the card, and the light stops for who limits animations.

import { test, expect } from '@playwright/test'
import { LEADERBOARD, openLeaderboard } from './_fixtures/portal-leaderboard-page.js'

const CARDS = {
  gold: '.lb-hero',
  silver: '.pt-lb-podium-card.lb-metal--silver',
  bronze: '.pt-lb-podium-card.lb-metal--bronze',
}

const readAngles = page =>
  page.evaluate(
    selectors =>
      selectors.map(selector =>
        parseFloat(
          getComputedStyle(document.querySelector(selector)).getPropertyValue('--lb-metal-angle'),
        ),
      ),
    Object.values(CARDS),
  )

test.describe('On a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  for (const [metal, selector] of Object.entries(CARDS)) {
    test(`the ${metal} frame is made of metal, with nothing shining around it`, async ({
      page,
    }) => {
      await openLeaderboard(page, 1280, LEADERBOARD)
      const look = await page.locator(selector).evaluate(card => {
        const style = getComputedStyle(card)
        return {
          width: style.borderTopWidth,
          color: style.borderTopColor,
          frame: style.backgroundImage.includes('conic-gradient'),
          shadow: style.boxShadow,
          after: getComputedStyle(card, '::after').content,
        }
      })
      expect(look).toEqual({
        width: '2px',
        color: 'rgba(0, 0, 0, 0)',
        frame: true,
        shadow: 'none',
        after: 'none',
      })
    })
  }

  for (const [metal, selector] of Object.entries(CARDS)) {
    test(`the ${metal} card rises a little under the pointer`, async ({ page }) => {
      await openLeaderboard(page, 1280, LEADERBOARD)
      await page.emulateMedia({ reducedMotion: 'no-preference' })
      const card = page.locator(selector)
      await card.scrollIntoViewIfNeeded()
      await page.mouse.move(0, 0)
      await expect(card).toHaveCSS('transform', 'none')
      await card.hover()
      await expect(card).toHaveCSS('transform', 'matrix(1, 0, 0, 1, 0, -4)')
      await expect(card).not.toHaveCSS('box-shadow', 'none')
    })

    test(`the ${metal} card stays still for who limits animations`, async ({ page }) => {
      await openLeaderboard(page, 1280, LEADERBOARD)
      const card = page.locator(selector)
      await card.scrollIntoViewIfNeeded()
      await card.hover()
      await expect(card).toHaveCSS('transform', 'none')
      await expect(card).toHaveCSS('transition-duration', '0s')
    })
  }

  test('the three metals differ, from the tokens of each', async ({ page }) => {
    await openLeaderboard(page, 1280, LEADERBOARD)
    const metals = await page.evaluate(selectors => {
      const swatch = document.createElement('i')
      document.body.append(swatch)
      const token = name => {
        swatch.style.color = `var(${name})`
        return getComputedStyle(swatch).color
      }
      const read = selector => {
        const card = document.querySelector(selector)
        swatch.style.color = getComputedStyle(card).getPropertyValue('--lb-metal-light')
        return getComputedStyle(swatch).color
      }
      const facts = {
        gold: [read(selectors.gold), token('--portal-tier-gold-c1')],
        silver: [read(selectors.silver), token('--portal-tier-silver-c1')],
        bronze: [read(selectors.bronze), token('--portal-tier-bronze-light')],
      }
      swatch.remove()
      return facts
    }, CARDS)
    for (const [actual, expected] of Object.values(metals)) {
      expect(actual).toBe(expected)
      expect(actual).not.toBe('rgba(0, 0, 0, 0)')
    }
    expect(new Set(Object.values(metals).map(([actual]) => actual)).size).toBe(3)
  })

  test('the figures, the medals and the XP of the podium take the color of their metal', async ({
    page,
  }) => {
    await openLeaderboard(page, 1280, LEADERBOARD)
    const cards = await page.locator('.pt-lb-podium-card').evaluateAll(items =>
      items.map(card => {
        const swatch = document.createElement('i')
        swatch.style.color = getComputedStyle(card).getPropertyValue('--lb-metal-light')
        document.body.append(swatch)
        const light = getComputedStyle(swatch).color
        swatch.remove()
        const rank = getComputedStyle(card.querySelector('.pt-lb-podium-rank'))
        return {
          light,
          medal: getComputedStyle(card.querySelector('.pt-lb-podium-medal')).color,
          xp: getComputedStyle(card.querySelector('.pt-lb-podium-xp')).color,
          clip: rank.backgroundClip,
          text: rank.color,
          size: rank.fontSize,
        }
      }),
    )
    expect(cards).toHaveLength(2)
    for (const card of cards) {
      expect(card.medal).toBe(card.light)
      expect(card.xp).toBe(card.light)
      expect(card.clip).toBe('text')
      expect(card.text).toBe('rgba(0, 0, 0, 0)')
      expect(card.size).toBe('32px')
    }
    const first = await page.locator('.lb-hero-rank-num').evaluate(rank => {
      const style = getComputedStyle(rank)
      return { clip: style.backgroundClip, text: style.color, image: style.backgroundImage }
    })
    expect(first.clip).toBe('text')
    expect(first.text).toBe('rgba(0, 0, 0, 0)')
    expect(first.image).toContain('linear-gradient')
  })

  test('the light turns, at its own place on each card', async ({ page }) => {
    await openLeaderboard(page, 1280, LEADERBOARD)
    await page.emulateMedia({ reducedMotion: 'no-preference' })
    const before = await readAngles(page)
    const frame = () =>
      page.locator('.lb-hero').evaluate(card => getComputedStyle(card).backgroundImage)
    const frameBefore = await frame()
    await page.waitForTimeout(400)
    const after = await readAngles(page)
    for (const [index, angle] of before.entries()) expect(after[index]).not.toBe(angle)
    expect(new Set(before.map(Math.round)).size).toBe(3)
    // What the eye sees: the drawing of the frame follows the angle.
    expect(await frame()).not.toBe(frameBefore)
  })

  test('the light stays still for who limits animations', async ({ page }) => {
    await openLeaderboard(page, 1280, LEADERBOARD)
    const before = await readAngles(page)
    await page.waitForTimeout(300)
    expect(await readAngles(page)).toEqual(before)
    expect(before).toEqual([135, 135, 135])
    const names = await page.evaluate(
      selectors =>
        selectors.map(selector => getComputedStyle(document.querySelector(selector)).animationName),
      Object.values(CARDS),
    )
    expect(new Set(names)).toEqual(new Set(['none']))
  })

  test('the rows of the top ten stay without a frame of metal', async ({ page }) => {
    await openLeaderboard(page, 1280, LEADERBOARD)
    await expect(page.locator('.lb-top-row').first()).toBeVisible()
    await expect(page.locator('.lb-top-row.lb-metal, .lb-rest .lb-metal')).toHaveCount(0)
  })
})

test.describe('On a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone')

  for (const width of [320, 375]) {
    test(`at ${width}px, the frames hold inside the screen, the rank clear of the avatar`, async ({
      page,
    }) => {
      await openLeaderboard(page, width, LEADERBOARD)
      const cards = await page.locator('.lb-metal').evaluateAll(items =>
        items.map(card => {
          const rank = card.querySelector('.pt-lb-podium-rank')?.getBoundingClientRect()
          const avatar = card.querySelector('.gc-lb-av')?.getBoundingClientRect()
          return {
            right: card.getBoundingClientRect().right,
            border: getComputedStyle(card).borderTopWidth,
            clear: !rank || rank.right <= avatar.left,
          }
        }),
      )
      expect(cards).toHaveLength(3)
      for (const card of cards) {
        expect(card.right).toBeLessThanOrEqual(width)
        expect(card.border).toBe('2px')
        expect(card.clear).toBe(true)
      }
    })
  }
})
