/**
 * Home data: a hero list is shown only once its availability is stamped (the
 * banner would otherwise offer "Request" on a title Emby holds), ordinary
 * rows do not wait, and the hero does not rotate under reduced motion nor
 * once the page is left.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  checkAvailability: vi.fn(),
  getAvailability: vi.fn(),
  checkStatus: vi.fn(),
}))

vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet: mocks.apiGet }) }))
vi.mock('@/composables/portal/useAvailability', () => ({
  useAvailability: () => ({
    checkAvailability: mocks.checkAvailability,
    getAvailability: mocks.getAvailability,
  }),
}))
vi.mock('@/composables/portal/useRequestStatus', () => ({
  useRequestStatus: () => ({ checkStatus: mocks.checkStatus, clearCache: vi.fn() }),
}))

import { usePortalHomeData } from '@/composables/portal/usePortalHomeData'

const ROWS = {
  '/api/portal/catalog/trending': {
    items: [
      { id: 11, tmdb_id: 11, media_type: 'movie', title: 'Sample One' },
      { id: 12, tmdb_id: 12, media_type: 'movie', title: 'Sample Two' },
    ],
  },
  '/api/portal/top20': { items: [{ id: 21, tmdb_id: 21, media_type: 'movie', title: 'Row' }] },
}

function mountHome() {
  let home
  const w = mount(
    defineComponent({
      setup() {
        home = usePortalHomeData()
        return () => h('div')
      },
    }),
  )
  return { w, home }
}

describe('usePortalHomeData', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.apiGet.mockImplementation(async url => ROWS[url] ?? { items: [] })
    mocks.getAvailability.mockImplementation(id =>
      id === 11 ? { availability: 'full', emby_url: 'http://emby.invalid/11' } : null,
    )
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('shows a hero title only once its availability is stamped', async () => {
    let release
    mocks.checkAvailability.mockReturnValue(
      new Promise(resolve => {
        release = resolve
      }),
    )
    const { w, home } = mountHome()

    const loading = home.loadAllData()
    await flushPromises()

    expect(home.heroItems.value).toEqual([])
    expect(home.top20.value).toHaveLength(1)

    release()
    await loading

    expect(home.heroItems.value[0]).toMatchObject({
      tmdb_id: 11,
      availability: 'full',
      emby_url: 'http://emby.invalid/11',
    })
    w.unmount()
  })

  it('holds the hero still under reduced motion, resumes once switched off', async () => {
    vi.useFakeTimers()
    const mql = { matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => mql),
    )
    const { w, home } = mountHome()
    await home.loadAllData()

    vi.advanceTimersByTime(30000)
    expect(home.heroIndex.value).toBe(0)

    mql.addEventListener.mock.calls[0][1]({ matches: false })
    await nextTick()
    vi.advanceTimersByTime(10000)
    expect(home.heroIndex.value).toBe(1)
    w.unmount()
  })

  it('stops the rotation once reduced motion is switched on', async () => {
    vi.useFakeTimers()
    const mql = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => mql),
    )
    const { w, home } = mountHome()
    await home.loadAllData()

    vi.advanceTimersByTime(10000)
    expect(home.heroIndex.value).toBe(1)

    mql.addEventListener.mock.calls[0][1]({ matches: true })
    await nextTick()
    vi.advanceTimersByTime(30000)
    expect(home.heroIndex.value).toBe(1)
    w.unmount()
  })

  it('starts no rotation once the page is left before the banner loads', async () => {
    vi.useFakeTimers()
    let release
    mocks.checkAvailability.mockReturnValue(
      new Promise(resolve => {
        release = resolve
      }),
    )
    const { w, home } = mountHome()
    const loading = home.loadAllData()

    w.unmount()
    release()
    await loading

    expect(vi.getTimerCount()).toBe(0)
  })
})
