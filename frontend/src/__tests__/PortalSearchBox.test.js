/**
 * Covers PortalSearchBox: submit routing, recent searches storage,
 * debounced suggestions, stale-response guard and keyboard navigation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const apiGet = vi.fn()
const routerPush = vi.fn().mockResolvedValue(undefined)
const routerReplace = vi.fn().mockResolvedValue(undefined)
const routeQ = ref(undefined)
const routeName = ref('portal-home')

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

vi.mock('vue-router', () => ({
  useRoute: () => ({
    get name() {
      return routeName.value
    },
    get query() {
      return { q: routeQ.value }
    },
  }),
  useRouter: () => ({
    push: routerPush,
    replace: routerReplace,
  }),
}))

vi.mock('lucide-vue-next', () => ({
  ArrowRight: { name: 'ArrowRightStub', template: '<i />' },
  Clock: { name: 'ClockStub', template: '<i />' },
  Search: { name: 'SearchStub', template: '<i />' },
}))

import PortalSearchBox from '@/components/portal/PortalSearchBox.vue'
import {
  useRecentSearches,
  __recent_search_constants,
} from '@/composables/portal/usePortalSearchHistory'

const RECENT_KEY = __recent_search_constants.RECENT_KEY

function buildBox() {
  return mount(PortalSearchBox, { attachTo: document.body })
}

function resetSharedState() {
  // The composable holds module-level state — clear it via the public API
  // so tests stay isolated.
  const { clear } = useRecentSearches()
  clear()
}

beforeEach(() => {
  apiGet.mockReset()
  routerPush.mockClear()
  routerReplace.mockClear()
  routeQ.value = undefined
  routeName.value = 'portal-home'
  if (typeof localStorage !== 'undefined') localStorage.clear()
  resetSharedState()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('PortalSearchBox — submit', () => {
  it('preserves the existing submit behavior (push to portal-search with q)', async () => {
    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.setValue('  Inception  ')
    await w.get('form').trigger('submit')
    await flushPromises()

    expect(routerPush).toHaveBeenCalledWith({
      name: 'portal-search',
      query: { q: 'Inception' },
    })
    w.unmount()
  })

  it('uses replace when already on the search route with a different query', async () => {
    routeName.value = 'portal-search'
    routeQ.value = 'old'
    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.setValue('matrix')
    await w.get('form').trigger('submit')
    await flushPromises()

    expect(routerReplace).toHaveBeenCalledWith({
      name: 'portal-search',
      query: { q: 'matrix' },
    })
    expect(routerPush).not.toHaveBeenCalled()
    w.unmount()
  })

  it('does not navigate when submitting an empty query', async () => {
    const w = buildBox()
    await flushPromises()

    await w.get('form').trigger('submit')
    await flushPromises()

    expect(routerPush).not.toHaveBeenCalled()
    expect(routerReplace).not.toHaveBeenCalled()
    w.unmount()
  })
})

describe('PortalSearchBox — recent searches', () => {
  it('caps history at 5 entries and dedupes case-insensitively', async () => {
    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')

    for (const value of ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta']) {
      await input.setValue(value)
      await w.get('form').trigger('submit')
      await flushPromises()
    }

    // Submit 'ALPHA' to test case-insensitive dedupe
    await input.setValue('ALPHA')
    await w.get('form').trigger('submit')
    await flushPromises()

    const stored = JSON.parse(localStorage.getItem(RECENT_KEY))
    expect(stored).toHaveLength(5)
    expect(stored[0]).toBe('ALPHA')
    // 'alpha' must have been removed by the case-insensitive dedupe
    expect(stored.find(v => v === 'alpha')).toBeUndefined()
    w.unmount()
  })

  it('exposes a clear button that empties recents and storage', async () => {
    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.setValue('inception')
    await w.get('form').trigger('submit')
    await flushPromises()

    routerPush.mockClear()
    routerReplace.mockClear()

    // Empty the field then re-focus so the popover renders the recent-searches
    // section (with its clear button) instead of the suggestions section.
    await input.setValue('')
    await input.trigger('focus')
    await flushPromises()

    const clearBtn = w.get('.pt-search-clear')
    await clearBtn.trigger('mousedown')
    await clearBtn.trigger('click')
    await flushPromises()

    expect(localStorage.getItem(RECENT_KEY)).toBeNull()
    w.unmount()
  })

  it('tolerates a corrupted localStorage payload without crashing', async () => {
    localStorage.setItem(RECENT_KEY, '{not valid json')
    const w = buildBox()
    await flushPromises()
    expect(w.exists()).toBe(true)
    w.unmount()
  })
})

describe('PortalSearchBox — suggestions', () => {
  it('does not query suggestions for queries shorter than 2 chars', async () => {
    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.trigger('focus')
    await input.setValue('a')
    await vi.advanceTimersByTimeAsync(400)

    expect(apiGet).not.toHaveBeenCalled()
    w.unmount()
  })

  it('debounces fetches and only fires after the delay', async () => {
    apiGet.mockResolvedValue({ items: [] })
    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.trigger('focus')

    await input.setValue('inc')
    await vi.advanceTimersByTimeAsync(100)
    await input.setValue('ince')
    await vi.advanceTimersByTimeAsync(100)
    await input.setValue('incep')
    expect(apiGet).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(260)
    await flushPromises()

    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiGet.mock.calls[0][0]).toBe('/api/portal/catalog/search?q=incep&page=1')
    w.unmount()
  })

  it('ignores a stale response if the user has typed a newer query', async () => {
    let resolveFirst
    const firstPromise = new Promise(resolve => {
      resolveFirst = resolve
    })
    let resolveSecond
    const secondPromise = new Promise(resolve => {
      resolveSecond = resolve
    })

    apiGet.mockImplementationOnce(() => firstPromise).mockImplementationOnce(() => secondPromise)

    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.trigger('focus')

    await input.setValue('alpha')
    await vi.advanceTimersByTimeAsync(260)
    await flushPromises()

    // Fire a second query while the first is still in-flight
    await input.setValue('beta')
    await vi.advanceTimersByTimeAsync(260)
    await flushPromises()

    // Resolve in reverse order: the first (stale) response must be ignored
    resolveSecond({ items: [{ tmdb_id: 1, title: 'Beta Movie', media_type: 'movie' }] })
    await flushPromises()
    resolveFirst({ items: [{ tmdb_id: 99, title: 'Alpha Movie', media_type: 'movie' }] })
    await flushPromises()

    const html = w.html()
    expect(html).toContain('Beta Movie')
    expect(html).not.toContain('Alpha Movie')
    w.unmount()
  })
})

describe('PortalSearchBox — keyboard navigation', () => {
  it('ArrowDown then Enter selects the active suggestion and navigates', async () => {
    apiGet.mockResolvedValue({
      items: [
        { tmdb_id: 1, title: 'Alpha Title', media_type: 'movie', year: 2020 },
        { tmdb_id: 2, title: 'Beta Title', media_type: 'movie', year: 2021 },
      ],
    })

    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.trigger('focus')
    await input.setValue('alp')
    await vi.advanceTimersByTimeAsync(260)
    await flushPromises()

    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(routerPush).toHaveBeenCalledWith({
      name: 'portal-search',
      query: { q: 'Alpha Title' },
    })
    w.unmount()
  })

  it('Escape closes the popover without navigating', async () => {
    const w = buildBox()
    await flushPromises()

    // Seed a recent so the popover opens on focus
    const { add } = useRecentSearches()
    add('previous query')

    const input = w.get('.pt-search-input')
    await input.trigger('focus')
    await flushPromises()

    expect(input.attributes('aria-expanded')).toBe('true')

    await input.trigger('keydown', { key: 'Escape' })
    await flushPromises()

    expect(input.attributes('aria-expanded')).toBe('false')
    expect(routerPush).not.toHaveBeenCalled()
    w.unmount()
  })
})

describe('PortalSearchBox — instance scoping', () => {
  it('produces unique combobox/listbox ids when two boxes co-exist in the same app', async () => {
    // PortalNav mounts the search box twice (topbar + drawer) inside one Vue
    // app, so the test must mirror that — useId() is app-scoped, not global,
    // and distinct mount() calls each spin up their own app.
    const Host = {
      components: { PortalSearchBox },
      template: `
        <div>
          <PortalSearchBox class="box-a" />
          <PortalSearchBox class="box-b" />
        </div>
      `,
    }
    const w = mount(Host, { attachTo: document.body })
    await flushPromises()

    const inputs = w.findAll('.pt-search-input')
    expect(inputs).toHaveLength(2)
    const inputA = inputs[0].attributes('id')
    const inputB = inputs[1].attributes('id')
    const listboxA = inputs[0].attributes('aria-controls')
    const listboxB = inputs[1].attributes('aria-controls')

    expect(inputA).toBeTruthy()
    expect(inputB).toBeTruthy()
    expect(inputA).not.toBe(inputB)
    expect(listboxA).not.toBe(listboxB)
    w.unmount()
  })
})

describe('PortalSearchBox — suggestion freshness', () => {
  it('does not show "no suggestions" while the debounce is still pending', async () => {
    apiGet.mockResolvedValue({ items: [] })
    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.trigger('focus')
    await input.setValue('xy')
    await flushPromises()

    // Debounce timer hasn't fired yet — must show searching, never empty state
    expect(w.html()).toContain('portal.search.searching')
    expect(w.html()).not.toContain('portal.search.noSuggestions')

    // Even partway through the debounce window the empty state must stay hidden
    await vi.advanceTimersByTimeAsync(100)
    await flushPromises()
    expect(w.html()).not.toContain('portal.search.noSuggestions')

    // Once the fetch completes, the empty state is allowed
    await vi.advanceTimersByTimeAsync(200)
    await flushPromises()
    expect(w.html()).toContain('portal.search.noSuggestions')
    w.unmount()
  })

  it('hides previous-query suggestions as soon as the user keeps typing', async () => {
    let resolveFirst
    apiGet
      .mockImplementationOnce(
        () =>
          new Promise(resolve => {
            resolveFirst = resolve
          }),
      )
      .mockImplementation(() => new Promise(() => {}))

    const w = buildBox()
    await flushPromises()

    const input = w.get('.pt-search-input')
    await input.trigger('focus')
    await input.setValue('alpha')
    await vi.advanceTimersByTimeAsync(260)
    await flushPromises()

    resolveFirst({ items: [{ tmdb_id: 1, title: 'Alpha One', media_type: 'movie' }] })
    await flushPromises()

    expect(w.html()).toContain('Alpha One')

    // Edit the query — previous results must vanish immediately, the empty
    // state must NOT appear (the new fetch hasn't run yet).
    await input.setValue('alphab')
    await flushPromises()

    expect(w.html()).not.toContain('Alpha One')
    expect(w.html()).not.toContain('portal.search.noSuggestions')
    expect(w.html()).toContain('portal.search.searching')
    w.unmount()
  })
})
