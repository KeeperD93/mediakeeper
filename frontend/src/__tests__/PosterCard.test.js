import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  return {
    ...actual,
    // Echo the key back so tests can match on the i18n token directly.
    useI18n: () => ({ t: key => key }),
  }
})

import PosterCard from '@/components/portal/PosterCard.vue'

const stubs = {
  PremiumRibbon: {
    name: 'PremiumRibbon',
    props: ['label', 'bg', 'count', 'pulse', 'title'],
    template:
      '<div class="stub-ribbon" :data-label="label" :data-bg="bg" :data-title="title || \'\'" />',
  },
  Bookmark: { template: '<span />' },
  EyeOff: { template: '<span />' },
  Plus: { template: '<span />' },
  Clock: { template: '<span />' },
  RotateCcw: { template: '<span />' },
  Star: { template: '<span />' },
}

function mountCard(props = {}) {
  return mount(PosterCard, {
    props: { title: 'Inception', ...props },
    global: { stubs },
  })
}

describe('PosterCard — primary action', () => {
  it('renders the PLAY button and emits play when availability is full', async () => {
    const w = mountCard({ availability: 'full' })
    const btn = w.find('button.mk-btn')
    expect(btn.classes()).toContain('mk-btn--play')
    expect(btn.attributes('disabled')).toBeUndefined()
    expect(btn.text()).toContain('portal.posterCard.actionPlay')
    await btn.trigger('click')
    expect(w.emitted('play')).toHaveLength(1)
    expect(w.emitted('request')).toBeUndefined()
  })

  it('renders an aria-disabled PENDING button when status is pending and emits nothing', async () => {
    const w = mountCard({ status: 'pending' })
    const btn = w.find('button.mk-btn')
    expect(btn.classes()).toContain('mk-btn--muted')
    // Spec R5: the muted CTA exposes aria-disabled (not the HTML disabled
    // attribute) so the click handler can still strip focus and release
    // the sticky :hover state on desktop.
    expect(btn.attributes('aria-disabled')).toBe('true')
    expect(btn.attributes('disabled')).toBeUndefined()
    expect(btn.text()).toContain('portal.posterCard.actionPending')
    await btn.trigger('click')
    expect(w.emitted('play')).toBeUndefined()
    expect(w.emitted('request')).toBeUndefined()
  })

  it('renders RE-REQUEST and emits request when status is rejected', async () => {
    const w = mountCard({ status: 'rejected', count: 3 })
    const btn = w.find('button.mk-btn')
    expect(btn.classes()).toContain('mk-btn--request')
    expect(btn.text()).toContain('portal.posterCard.actionReRequest')
    await btn.trigger('click')
    expect(w.emitted('request')).toHaveLength(1)
  })

  it('renders REQUEST by default and emits request on click', async () => {
    const w = mountCard({})
    const btn = w.find('button.mk-btn')
    expect(btn.classes()).toContain('mk-btn--request')
    expect(btn.text()).toContain('portal.posterCard.actionRequest')
    await btn.trigger('click')
    expect(w.emitted('request')).toHaveLength(1)
  })
})

describe('PosterCard — status ribbon + tokens', () => {
  it('does not render a ribbon when status and isNew are absent', () => {
    const w = mountCard({ availability: 'full' })
    expect(w.find('.stub-ribbon').exists()).toBe(false)
  })

  it('renders the NEW ribbon with the success token color when isNew is true', () => {
    const w = mountCard({ isNew: true })
    const ribbon = w.find('.stub-ribbon')
    expect(ribbon.exists()).toBe(true)
    expect(ribbon.attributes('data-bg')).toBe('var(--portal-color-success)')
    expect(ribbon.attributes('data-label')).toBe('portal.posterCard.badgeNew')
  })

  it('routes the rejected status to the error token and uppercased label', () => {
    const w = mountCard({ status: 'rejected', count: 2 })
    const ribbon = w.find('.stub-ribbon')
    expect(ribbon.attributes('data-bg')).toBe('var(--portal-color-error)')
    // Computed status label is uppercased via JS, not via CSS.
    expect(ribbon.attributes('data-label')).toBe('PORTAL.POSTERCARD.STATUSREJECTED')
  })

  it('routes the watched status to the premium token', () => {
    const w = mountCard({ status: 'watched' })
    const ribbon = w.find('.stub-ribbon')
    expect(ribbon.attributes('data-bg')).toBe('var(--portal-color-premium)')
  })
})

describe('PosterCard — bookmark + blacklist emits', () => {
  it('emits toggle-bookmark when the bookmark icon is clicked', async () => {
    const w = mountCard({})
    const bookmarkBtn = w.findAll('button.mk-iconbtn')[0]
    await bookmarkBtn.trigger('click')
    expect(w.emitted('toggle-bookmark')).toHaveLength(1)
  })

  it('hides the blacklist button by default (showBlacklist=false)', () => {
    const w = mountCard({})
    const iconBtns = w.findAll('button.mk-iconbtn')
    // Bookmark stays, blacklist is gated behind showBlacklist.
    expect(iconBtns).toHaveLength(1)
  })

  it('renders the blacklist button when showBlacklist is true', async () => {
    const w = mountCard({ showBlacklist: true })
    const iconBtns = w.findAll('button.mk-iconbtn')
    expect(iconBtns).toHaveLength(2)
    await iconBtns[1].trigger('click')
    expect(w.emitted('toggle-blacklist')).toHaveLength(1)
  })

  it('applies the gold modifier on the bookmark button when bookmarked is true', () => {
    const w = mountCard({ bookmarked: true })
    const buttons = w.findAll('button.mk-iconbtn')
    expect(buttons[0].classes()).toContain('mk-iconbtn--gold')
  })

  it('applies the red modifier on the blacklist button when blacklisted+showBlacklist', () => {
    const w = mountCard({ blacklisted: true, showBlacklist: true })
    const buttons = w.findAll('button.mk-iconbtn')
    expect(buttons[1].classes()).toContain('mk-iconbtn--red')
  })
})

describe('PosterCard — availability chip', () => {
  it('renders the full chip when availability is full', () => {
    const w = mountCard({ availability: 'full' })
    const chip = w.find('.mk-poster__avail')
    expect(chip.exists()).toBe(true)
    expect(chip.classes()).toContain('mk-poster__avail--full')
    expect(chip.text()).toContain('portal.posterCard.availFull')
  })

  it('renders the partial chip when availability is partial', () => {
    const w = mountCard({ availability: 'partial' })
    const chip = w.find('.mk-poster__avail')
    expect(chip.classes()).toContain('mk-poster__avail--partial')
    expect(chip.text()).toContain('portal.posterCard.availPartial')
  })
})

describe('PosterCard — rank medals', () => {
  it('adds no rank class when rank is null', () => {
    const w = mountCard({})
    expect(w.classes()).not.toContain('mk-poster--rank-1')
    expect(w.classes()).not.toContain('mk-poster--rank-2')
    expect(w.classes()).not.toContain('mk-poster--rank-3')
  })

  it('applies the gold medal class when rank is 1', () => {
    const w = mountCard({ rank: 1 })
    expect(w.classes()).toContain('mk-poster--rank-1')
  })

  it('applies the silver medal class when rank is 2', () => {
    const w = mountCard({ rank: 2 })
    expect(w.classes()).toContain('mk-poster--rank-2')
  })

  it('applies the bronze medal class when rank is 3', () => {
    const w = mountCard({ rank: 3 })
    expect(w.classes()).toContain('mk-poster--rank-3')
  })
})

describe('PosterCard — TMDB rating', () => {
  it('renders the star + percentage (vote*10) with an i18n aria-label when rating is set', () => {
    const w = mountCard({ rating: 7.5 })
    const r = w.find('.mk-poster__rating')
    expect(r.exists()).toBe(true)
    expect(r.text()).toContain('75%')
    // The $t stub serialises params as `key:{json}`, so assert the i18n key
    // is used AND the pct (75) is forwarded to it.
    expect(r.attributes('aria-label')).toContain('portal.posterCard.tmdbRating')
    expect(r.attributes('aria-label')).toContain('75')
  })

  it('hides the rating when rating is 0 or absent', () => {
    expect(mountCard({ rating: 0 }).find('.mk-poster__rating').exists()).toBe(false)
    expect(mountCard({}).find('.mk-poster__rating').exists()).toBe(false)
  })
})

describe('PosterCard — mobile caption', () => {
  it('renders the title and year under the poster', () => {
    const w = mountCard({ title: 'Dune', year: '2021' })
    const info = w.find('.mk-poster__info')
    expect(info.exists()).toBe(true)
    expect(info.find('.mk-poster__info-title').text()).toBe('Dune')
    expect(info.find('.mk-poster__info-year').text()).toBe('2021')
  })

  it('omits the year line when year is absent', () => {
    const w = mountCard({ title: 'Dune' })
    expect(w.find('.mk-poster__info-title').text()).toBe('Dune')
    expect(w.find('.mk-poster__info-year').exists()).toBe(false)
  })

  it('shows the rating next to the date in the caption', () => {
    const w = mountCard({ title: 'Dune', year: '2021', rating: 8.4 })
    const meta = w.find('.mk-poster__info-meta')
    expect(meta.find('.mk-poster__info-year').text()).toBe('2021')
    const r = meta.find('.mk-poster__info-rating')
    expect(r.exists()).toBe(true)
    expect(r.text()).toContain('84%')
  })
})

describe('PosterCard — ribbon tooltip', () => {
  it('forwards the tooltip prop to the PremiumRibbon title prop on a status ribbon', () => {
    const w = mountCard({ status: 'rejected', tooltip: 'Rejected on May 10, 2026' })
    const ribbon = w.find('.stub-ribbon')
    expect(ribbon.exists()).toBe(true)
    expect(ribbon.attributes('data-title')).toBe('Rejected on May 10, 2026')
  })

  it('forwards the tooltip prop to the NEW ribbon as well', () => {
    const w = mountCard({ isNew: true, tooltip: 'Added on May 14, 2026' })
    const ribbon = w.find('.stub-ribbon')
    expect(ribbon.attributes('data-title')).toBe('Added on May 14, 2026')
  })

  it('leaves the data-title empty when no tooltip is provided', () => {
    const w = mountCard({ status: 'approved' })
    const ribbon = w.find('.stub-ribbon')
    expect(ribbon.attributes('data-title')).toBe('')
  })
})
