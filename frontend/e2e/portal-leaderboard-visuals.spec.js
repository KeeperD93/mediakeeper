// Look of the leaderboard: the crown sits in the corner of its card, nothing glows
// around the cards, the icons of the figures bar stand out without looking like
// its text, and the trophies won are gold, next to a green lead without an icon.

import { test, expect } from '@playwright/test'
import { LEADERBOARD, openLeaderboard, viewerInList } from './_fixtures/portal-leaderboard-page.js'

// In the corner of the card, like the medals of the podium, and clear of a long name.
async function expectCrownInCorner(page) {
  const boxes = await page.locator('.lb-hero').evaluate(card => {
    const name = card.querySelector('.lb-hero-name')
    const nameBox = name.getBoundingClientRect()
    return {
      crown: card.querySelector('.lb-hero-crown').getBoundingClientRect().toJSON(),
      card: card.getBoundingClientRect().toJSON(),
      nameTop: nameBox.top,
      // A long name is cut at the end of its content box, padding excluded.
      nameEnd: nameBox.right - parseFloat(getComputedStyle(name).paddingRight),
    }
  })
  expect(boxes.crown.top - boxes.card.top).toBeLessThanOrEqual(15)
  expect(boxes.card.right - boxes.crown.right).toBeLessThanOrEqual(15)
  expect(boxes.crown.right).toBeLessThanOrEqual(boxes.card.right)
  if (boxes.nameTop < boxes.crown.bottom) {
    expect(boxes.nameEnd).toBeLessThanOrEqual(boxes.crown.left)
  }
}

async function expectNoHalo(page) {
  const styles = await page.evaluate(() => {
    const root = document.querySelector('.pt-leaderboard')
    const hero = document.querySelector('.lb-hero')
    return {
      backdrop: ['::before', '::after'].map(part => getComputedStyle(root, part).content),
      heroVeil: getComputedStyle(hero, '::after').content,
      rankGlow: getComputedStyle(document.querySelector('.lb-hero-rank-num')).textShadow,
      cards: [...document.querySelectorAll('.lb-hero, .pt-lb-podium-card')].map(card => {
        const style = getComputedStyle(card)
        return [style.boxShadow, style.backgroundImage]
      }),
    }
  })
  expect(styles.backdrop).toEqual(['none', 'none'])
  expect(styles.heroVeil).toBe('none')
  expect(styles.rankGlow).toBe('none')
  expect(styles.cards).toHaveLength(3)
  for (const card of styles.cards) expect(card).toEqual(['none', 'none'])
}

// The light indigo of the portal on every icon of the bar, set apart from its text.
async function expectStatsIconsVisible(page) {
  const colors = await page.evaluate(() => {
    const swatch = document.createElement('span')
    swatch.style.color = 'var(--portal-accent-400)'
    document.body.append(swatch)
    const expected = getComputedStyle(swatch).color
    swatch.remove()
    const bar = document.querySelector('.lb-stats-bar')
    return {
      expected,
      text: getComputedStyle(bar.querySelector('.lb-stats-chip-text')).color,
      icons: [...bar.querySelectorAll('.lb-stats-chip > svg:not(.lb-stats-progress)')].map(
        icon => getComputedStyle(icon).color,
      ),
      ring: getComputedStyle(bar.querySelector('.lb-stats-progress-fill')).stroke,
    }
  })
  expect(colors.icons).toHaveLength(4)
  expect(new Set(colors.icons)).toEqual(new Set([colors.expected]))
  expect(colors.ring).toBe(colors.expected)
  expect(colors.text).not.toBe(colors.expected)
}

async function expectTrophiesGold(page) {
  const look = await page.evaluate(() => {
    const swatch = document.createElement('span')
    swatch.style.color = 'var(--portal-color-warning)'
    document.body.append(swatch)
    const gold = getComputedStyle(swatch).color
    swatch.remove()
    const hero = document.querySelector('.lb-hero')
    return {
      gold,
      trophies: [...document.querySelectorAll('.lb-trophies')].map(
        chip => getComputedStyle(chip).color,
      ),
      leadColor: getComputedStyle(hero.querySelector('.lb-hero-lead')).color,
      leadIcon: !!hero.querySelector('.lb-hero-lead svg'),
      heroTrophyIcon: !!hero.querySelector('.lb-trophies svg'),
    }
  })
  expect(look.trophies.length).toBeGreaterThan(0)
  expect(new Set(look.trophies)).toEqual(new Set([look.gold]))
  expect(look.leadColor).not.toBe(look.gold)
  expect(look.leadIcon).toBe(false)
  expect(look.heroTrophyIcon).toBe(true)
}

test.describe('Look of the leaderboard on a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen layout only')

  test('stays sober and readable', async ({ page }) => {
    const tracker = await openLeaderboard(page, 1280, LEADERBOARD)
    await expectCrownInCorner(page)
    await expectNoHalo(page)
    await expectStatsIconsVisible(page)
    await expectTrophiesGold(page)
    expect(tracker.unexpected).toEqual([])
  })
})

test.describe('Look of the leaderboard on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout only')

  for (const width of [320, 375, 430, 767]) {
    test(`stays sober and readable at ${width}px`, async ({ page }) => {
      const tracker = await openLeaderboard(page, width, LEADERBOARD)
      await expectCrownInCorner(page)
      await expectNoHalo(page)
      await expectStatsIconsVisible(page)
      await expectTrophiesGold(page)
      expect(tracker.unexpected).toEqual([])
    })

    test(`keeps the crown clear of a first-place viewer at ${width}px`, async ({ page }) => {
      const tracker = await openLeaderboard(page, width, viewerInList(0))
      await expectCrownInCorner(page)
      expect(tracker.unexpected).toEqual([])
    })
  }
})
