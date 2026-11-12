/**
 * Statistics → General playback cards: a period that failed to load says so
 * and offers a retry of that period, instead of an empty section.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const h = vi.hoisted(() => ({ loadPlayback: vi.fn() }))
const playbackFailed = ref(true)

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useStats', () => ({
  useStats: () => ({
    playback: ref(null),
    loadingPlayback: ref(false),
    playbackFailed,
    loadPlayback: h.loadPlayback,
    resolveSeriesImageId: vi.fn(),
    ticksToHours: () => '0',
  }),
}))
vi.mock('@/composables/useStatsUI', () => ({
  useStatsUI: () => ({
    showPreview: vi.fn(),
    hidePreview: vi.fn(),
    openUserProfile: vi.fn(),
    goToActivitySearch: vi.fn(),
  }),
}))

import StatsPlaybackCards from '@/components/stats/StatsPlaybackCards.vue'

describe('StatsPlaybackCards', () => {
  it('says a failed load and retries the selected period', async () => {
    const w = mount(StatsPlaybackCards)
    await w.findAll('.pill').at(1).trigger('click') // 30 days
    h.loadPlayback.mockClear()

    const error = w.find('.pc-error')
    expect(error.text()).toContain('stats.playbackLoadError')
    await error.find('button').trigger('click')
    expect(h.loadPlayback).toHaveBeenCalledWith(30)

    playbackFailed.value = false
    await w.vm.$nextTick()
    expect(w.find('.pc-error').exists()).toBe(false)
  })
})
