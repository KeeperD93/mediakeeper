// Look of the leaderboard: the crown sits in the corner of its card, nothing glows
// around the cards, the icons of the figures bar stand out without looking like
// its text, and the trophies won are gold, next to a green lead without an icon.

import { test, expect } from '@playwright/test'
import {
  LEADERBOARD,
  openLeaderboard,
  roomAroundFigures,
  viewerInList,
} from './_fixtures/portal-leaderboard-page.js'

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

// The positions of the top ten read like those of the rows below: no bubble, same type,
// same color. The first three keep their large figures.
async function expectPlainPositions(page) {
  const look = await page.evaluate(() => {
    const read = element => {
      const style = getComputedStyle(element)
      return {
        family: style.fontFamily,
        size: style.fontSize,
        weight: style.fontWeight,
        color: style.color,
        background: style.backgroundColor,
        padding: style.paddingLeft,
      }
    }
    return {
      topTen: [...document.querySelectorAll('.lb-top-row-rank')].map(read),
      below: read(document.querySelector('.lb-rest .gc-lb-pos')),
      first: parseFloat(getComputedStyle(document.querySelector('.lb-hero-rank-num')).fontSize),
      podium: [...document.querySelectorAll('.pt-lb-podium-rank')].map(rank =>
        parseFloat(getComputedStyle(rank).fontSize),
      ),
    }
  })
  expect(look.topTen).toHaveLength(10)
  for (const position of look.topTen) expect(position).toEqual(look.below)
  expect(look.below.background).toBe('rgba(0, 0, 0, 0)')
  const plain = parseFloat(look.below.size)
  expect(look.first).toBeGreaterThan(plain)
  expect(look.podium).toHaveLength(2)
  for (const size of look.podium) expect(size).toBeGreaterThan(plain)
}

// The text of the green bubble starts under the first digit, not the bubble itself,
// and the bubble stays clear of the avatar.
async function expectLeadUnderDigits(page, margins) {
  const facts = await page.locator('.lb-hero').evaluate(card => {
    const textLeft = element => {
      const range = document.createRange()
      range.selectNodeContents(element)
      return range.getBoundingClientRect().left
    }
    const lead = card.querySelector('.lb-hero-lead')
    const style = getComputedStyle(lead)
    return {
      lead: textLeft(lead),
      digits: textLeft(card.querySelector('.lb-hero-xp-value')),
      bubble: lead.getBoundingClientRect().left,
      avatar: card.querySelector('.lb-hero-avatar').getBoundingClientRect().right,
      margins: { side: style.paddingLeft, top: style.paddingTop },
    }
  })
  expect(Math.abs(facts.lead - facts.digits)).toBeLessThanOrEqual(1)
  expect(facts.bubble).toBeLessThan(facts.digits)
  expect(facts.bubble).toBeGreaterThanOrEqual(facts.avatar)
  expect(facts.margins).toEqual(margins)
}

// As wide as its word, wherever the viewer stands, without the separator of the digest.
async function expectSmallLabel(page, rowSelector) {
  const row = page.locator(rowSelector)
  await expect(row.locator('.lb-me-pill')).toHaveText('VOUS')
  const facts = await row.evaluate(element => {
    const pill = element.querySelector('.lb-me-pill')
    const text = document.createRange()
    text.selectNodeContents(pill)
    return {
      height: pill.getBoundingClientRect().height,
      margin: pill.getBoundingClientRect().width - text.getBoundingClientRect().width,
      dashes: getComputedStyle(element, '::before').content,
    }
  })
  expect(facts.height).toBeLessThanOrEqual(12)
  expect(facts.margin).toBeLessThanOrEqual(10)
  expect(facts.dashes).toBe('none')
}

test.describe('Look of the leaderboard on a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen layout only')

  test('stays sober and readable', async ({ page }) => {
    const tracker = await openLeaderboard(page, 1280, LEADERBOARD)
    await expectCrownInCorner(page)
    await expectNoHalo(page)
    await expectStatsIconsVisible(page)
    await expectTrophiesGold(page)
    await expectPlainPositions(page)
    await expectLeadUnderDigits(page, { side: '12px', top: '4px' })
    expect(tracker.unexpected).toEqual([])
  })

  for (const [where, index, row] of [
    ['top ten', 6, '.lb-top-row--me'],
    ['rows below', 16, '.lb-rest .gc-lb-row--me'],
  ]) {
    test(`keeps the label of the viewer small in the ${where}`, async ({ page }) => {
      await openLeaderboard(page, 1280, viewerInList(index))
      await expectSmallLabel(page, row)
    })
  }
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
      await expectPlainPositions(page)
      await expectLeadUnderDigits(
        page,
        width <= 640 ? { side: '8px', top: '2px' } : { side: '12px', top: '4px' },
      )
      expect(tracker.unexpected).toEqual([])
    })

    if (width <= 640) {
      test(`centers the XP and the trophies in their row at ${width}px`, async ({ page }) => {
        await openLeaderboard(page, width, LEADERBOARD)
        for (const [rows, xp] of [
          ['.lb-top-row', '.lb-top-row-xp'],
          ['.lb-rest .gc-lb-row', '.gc-lb-v'],
        ]) {
          const room = await roomAroundFigures(page, rows, xp)
          expect(room.length).toBeGreaterThan(0)
          for (const row of room) expect(Math.abs(row.above - row.under)).toBeLessThanOrEqual(1)
        }
      })
    }

    test(`keeps the crown clear of a first-place viewer at ${width}px`, async ({ page }) => {
      const tracker = await openLeaderboard(page, width, viewerInList(0))
      await expectCrownInCorner(page)
      expect(tracker.unexpected).toEqual([])
    })
  }
})
