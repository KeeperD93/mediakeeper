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
    props: ['label', 'bg', 'count', 'pulse'],
    template: '<div class="stub-ribbon" :data-label="label" :data-bg="bg" />',
  },
  Bookmark: { template: '<span />' },
  EyeOff: { template: '<span />' },
  Plus: { template: '<span />' },
  Clock: { template: '<span />' },
  RotateCcw: { template: '<span />' },
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

  it('renders a disabled PENDING button when status is pending and emits nothing', async () => {
    const w = mountCard({ status: 'pending' })
    const btn = w.find('button.mk-btn')
    expect(btn.classes()).toContain('mk-btn--muted')
    expect(btn.attributes('disabled')).toBeDefined()
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
