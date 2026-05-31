/**
 * Covers useSettingsTabHash: hash deep links open the matching tab,
 * tab clicks rewrite the URL via router.replace, invalid or hidden
 * tabs fall back to identity, and the privacy tab respects the
 * GDPR opt-in flag.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { computed, nextTick, reactive } from 'vue'

import { tabFromHash, useSettingsTabHash } from '@/composables/portal/useSettingsTabHash'

const ALL_IDS = ['identity', 'appearance', 'preferences', 'visibility', 'account', 'privacy']
const NO_PRIVACY_IDS = ALL_IDS.filter(id => id !== 'privacy')

function makeHarness(initialHash, ids = NO_PRIVACY_IDS) {
  const route = reactive({ path: '/portal/settings', query: {}, hash: initialHash })
  const replace = vi.fn(target => {
    if (target?.hash !== undefined) route.hash = target.hash
    return Promise.resolve()
  })
  const router = { replace }
  const tabIds = reactive({ value: [...ids] })
  const visibleTabIds = computed(() => tabIds.value)
  return { route, router, replace, visibleTabIds, tabIds }
}

describe('tabFromHash', () => {
  it('strips the leading # and accepts visible tabs', () => {
    expect(tabFromHash('#appearance', ALL_IDS)).toBe('appearance')
    expect(tabFromHash('appearance', ALL_IDS)).toBe('appearance')
  })

  it('falls back to identity when the hash is empty, unknown, or hidden', () => {
    expect(tabFromHash('', ALL_IDS)).toBe('identity')
    expect(tabFromHash('#bogus', ALL_IDS)).toBe('identity')
    expect(tabFromHash('#privacy', NO_PRIVACY_IDS)).toBe('identity')
  })
})

describe('useSettingsTabHash', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens the tab matching the initial hash (#appearance → appearance)', () => {
    const { route, router, visibleTabIds } = makeHarness('#appearance')
    const { activeTab } = useSettingsTabHash(route, router, visibleTabIds)
    expect(activeTab.value).toBe('appearance')
  })

  it('rewrites the URL via router.replace when the active tab changes', async () => {
    const { route, router, replace, visibleTabIds } = makeHarness('#identity')
    const { activeTab } = useSettingsTabHash(route, router, visibleTabIds)
    replace.mockClear()

    activeTab.value = 'preferences'
    await nextTick()

    expect(replace).toHaveBeenCalledTimes(1)
    expect(replace.mock.calls[0][0]).toMatchObject({
      path: '/portal/settings',
      hash: '#preferences',
    })
    expect(route.hash).toBe('#preferences')
  })

  it('normalises an invalid hash to identity and rewrites the URL', async () => {
    const { route, router, replace, visibleTabIds } = makeHarness('#bogus')
    const { activeTab } = useSettingsTabHash(route, router, visibleTabIds)
    await nextTick()

    expect(activeTab.value).toBe('identity')
    expect(replace).toHaveBeenCalled()
    expect(route.hash).toBe('#identity')
  })

  it('accepts #privacy only when GDPR mode exposes the tab', () => {
    // GDPR off: privacy is hidden, falls back to identity.
    const off = makeHarness('#privacy', NO_PRIVACY_IDS)
    const offTab = useSettingsTabHash(off.route, off.router, off.visibleTabIds).activeTab
    expect(offTab.value).toBe('identity')

    // GDPR on: privacy is visible, the deep link sticks.
    const on = makeHarness('#privacy', ALL_IDS)
    const onTab = useSettingsTabHash(on.route, on.router, on.visibleTabIds).activeTab
    expect(onTab.value).toBe('privacy')
  })

  it('drops back to identity when the active tab is hidden mid-session', async () => {
    const { route, router, visibleTabIds, tabIds } = makeHarness('#privacy', ALL_IDS)
    const { activeTab } = useSettingsTabHash(route, router, visibleTabIds)
    expect(activeTab.value).toBe('privacy')

    tabIds.value = NO_PRIVACY_IDS
    await nextTick()

    expect(activeTab.value).toBe('identity')
  })

  it('syncs the URL when an upstream error forces the tab back to identity', async () => {
    const { route, router, replace, visibleTabIds } = makeHarness('#preferences')
    const { activeTab } = useSettingsTabHash(route, router, visibleTabIds)
    expect(activeTab.value).toBe('preferences')
    replace.mockClear()

    // Simulates the username-error branch in PortalSettings.onSave().
    activeTab.value = 'identity'
    await nextTick()

    expect(replace).toHaveBeenCalledTimes(1)
    expect(replace.mock.calls[0][0].hash).toBe('#identity')
    expect(route.hash).toBe('#identity')
  })

  it('uses router.replace (not push) so tab clicks do not stack history entries', async () => {
    const { route, router, replace, visibleTabIds } = makeHarness('#identity')
    const { activeTab } = useSettingsTabHash(route, router, visibleTabIds)
    replace.mockClear()

    activeTab.value = 'appearance'
    await nextTick()
    activeTab.value = 'account'
    await nextTick()

    expect(replace).toHaveBeenCalledTimes(2)
    // No push verb available on the harness — calling it would have thrown.
    expect(router.push).toBeUndefined()
  })
})
