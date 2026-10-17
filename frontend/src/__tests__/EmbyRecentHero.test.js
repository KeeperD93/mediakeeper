/**
 * Covers the "Play" button of the recently-added hero: it opens the current
 * title in Emby in a new tab, and never renders an unsafe link. The rotation
 * stops while the device asks for reduced motion.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'

vi.mock('@/composables/portal/useTrailer', () => ({
  useTrailer: () => ({ trailer: ref(null), candidates: ref([]), resolve: vi.fn() }),
}))

import EmbyRecentHero from '@/components/portal/EmbyRecentHero.vue'

function mountHero(...items) {
  return mount(EmbyRecentHero, {
    props: { items: items.map((item, i) => ({ id: i + 1, title: 'Movie', ...item })) },
    global: { stubs: { MediaCard: true, TrailerLightbox: true } },
  })
}

describe('EmbyRecentHero — Play button', () => {
  beforeEach(() => {
    // jsdom has no ResizeObserver; the rotation timer must not outlive a test.
    vi.useFakeTimers()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        disconnect() {}
      },
    )
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('opens the current title in Emby in a new tab', () => {
    const w = mountHero({ emby_url: 'http://emby.invalid/item' })
    const play = w.get('a.pt-eh-btn--play')
    expect(play.text()).toContain('portal.hero.play')
    expect(play.attributes('href')).toBe('http://emby.invalid/item')
    expect(play.attributes('target')).toBe('_blank')
    expect(play.attributes('rel')).toBe('noopener noreferrer')
    w.unmount()
  })

  it('follows the rotation to the title on screen', async () => {
    const w = mountHero(
      { emby_url: 'http://emby.invalid/first' },
      { emby_url: 'http://emby.invalid/second' },
    )

    vi.advanceTimersByTime(10000)
    await nextTick()

    expect(w.get('a.pt-eh-btn--play').attributes('href')).toBe('http://emby.invalid/second')
    w.unmount()
  })

  it('shows no Play button without a safe Emby link', () => {
    const w = mountHero({ emby_url: 'javascript:alert(1)' })
    expect(w.find('.pt-eh-btn--play').exists()).toBe(false)
    w.unmount()
  })

  it('holds still under reduced motion and resumes once it is switched off', async () => {
    const mql = { matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => mql),
    )
    const w = mountHero(
      { emby_url: 'http://emby.invalid/first' },
      { emby_url: 'http://emby.invalid/second' },
    )
    const playHref = () => w.get('a.pt-eh-btn--play').attributes('href')

    vi.advanceTimersByTime(30000)
    await nextTick()
    expect(playHref()).toBe('http://emby.invalid/first')

    mql.addEventListener.mock.calls[0][1]({ matches: false })
    await nextTick()
    vi.advanceTimersByTime(10000)
    await nextTick()
    expect(playHref()).toBe('http://emby.invalid/second')
    w.unmount()
  })

  it('stops rotating once reduced motion is switched on', async () => {
    const mql = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => mql),
    )
    const w = mountHero(
      { emby_url: 'http://emby.invalid/first' },
      { emby_url: 'http://emby.invalid/second' },
    )
    const playHref = () => w.get('a.pt-eh-btn--play').attributes('href')

    vi.advanceTimersByTime(10000)
    await nextTick()
    expect(playHref()).toBe('http://emby.invalid/second')

    mql.addEventListener.mock.calls[0][1]({ matches: true })
    await nextTick()
    vi.advanceTimersByTime(30000)
    await nextTick()
    expect(playHref()).toBe('http://emby.invalid/second')
    w.unmount()
  })
})
