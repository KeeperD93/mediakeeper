/**
 * Regression test for the TMDB enrichment URL — the previous code
 * passed `results[0].type` / `results[0].id`, which produced
 * `undefined/undefined` because the search endpoint returns
 * `media_type` and `tmdb_id`. The fix wires the correct field names;
 * this test pins that contract so a future refacto cannot silently
 * regress it.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet,
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    apiPatch: vi.fn(),
    apiFetch: vi.fn(),
    loading: { value: false },
    error: { value: null },
  }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('@/composables/useFocusTrap', () => ({
  useFocusTrap: vi.fn(),
}))

import NowPlayingFullscreen from '@/components/dashboard/NowPlayingFullscreen.vue'

describe('NowPlayingFullscreen — TMDB enrichment URL contract', () => {
  beforeEach(() => {
    apiGet.mockReset()
  })

  it('calls /api/watchlist/tmdb with the search result media_type + tmdb_id (no undefined)', async () => {
    apiGet.mockImplementation(url => {
      if (url.startsWith('/api/watchlist/search')) {
        return Promise.resolve([{ media_type: 'tv', tmdb_id: 12345, name: 'Foo' }])
      }
      if (url.startsWith('/api/watchlist/tmdb/')) {
        return Promise.resolve({ title: 'Foo', overview: 'Bar' })
      }
      return Promise.resolve(null)
    })

    // The watch on `visible` fires only on false→true transition (no
    // immediate flag), so we mount with visible=false then flip.
    const w = mount(NowPlayingFullscreen, {
      props: { visible: false, session: { series: 'Foo', media: 'Foo' } },
    })
    await w.setProps({ visible: true })
    await flushPromises()

    const tmdbCall = apiGet.mock.calls.find(c => c[0].startsWith('/api/watchlist/tmdb/'))
    expect(tmdbCall).toBeDefined()
    expect(tmdbCall[0]).toBe('/api/watchlist/tmdb/tv/12345')
    expect(tmdbCall[0]).not.toContain('undefined')
  })

  it('skips the enrichment fetch when the search returns no result', async () => {
    apiGet.mockImplementation(url => {
      if (url.startsWith('/api/watchlist/search')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    const w = mount(NowPlayingFullscreen, {
      props: { visible: false, session: { series: 'Empty', media: 'Empty' } },
    })
    await w.setProps({ visible: true })
    await flushPromises()

    const tmdbCall = apiGet.mock.calls.find(c => c[0].startsWith('/api/watchlist/tmdb/'))
    expect(tmdbCall).toBeUndefined()
  })

  it('does not call the TMDB API when the modal is not visible', async () => {
    mount(NowPlayingFullscreen, {
      props: { visible: false, session: { series: 'Foo' } },
    })
    await flushPromises()

    expect(apiGet).not.toHaveBeenCalled()
  })
})
