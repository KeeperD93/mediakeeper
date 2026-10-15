/**
 * Covers the "Play" button of the recently-added hero: it opens the current
 * title in Emby in a new tab, and never renders an unsafe link.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import { mount } from '@vue/test-utils'

vi.mock('@/composables/portal/useTrailer', () => ({
  useTrailer: () => ({ trailer: ref(null), candidates: ref([]), resolve: vi.fn() }),
}))

import EmbyRecentHero from '@/components/portal/EmbyRecentHero.vue'

function mountHero(item) {
  return mount(EmbyRecentHero, {
    props: { items: [{ id: 1, title: 'Movie', ...item }] },
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

  it('shows no Play button without a safe Emby link', () => {
    const w = mountHero({ emby_url: 'javascript:alert(1)' })
    expect(w.find('.pt-eh-btn--play').exists()).toBe(false)
    w.unmount()
  })
})
