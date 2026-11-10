/**
 * Statistics stays alive once left: its sessions are polled only while it is on screen.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive, ref } from 'vue'

const startSessionPolling = vi.fn()
const stopSessionPolling = vi.fn()
vi.mock('@/composables/useStats', () => ({
  useStats: () => ({ startSessionPolling, stopSessionPolling }),
}))
vi.mock('@/composables/useStatsUI', () => ({
  useStatsUI: () => ({
    activeTab: ref('general'),
    profileOpen: ref(false),
    mergeModal: reactive({ open: false }),
  }),
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, path: '/stats' }),
  useRouter: () => ({ replace: vi.fn() }),
}))
const { stub } = vi.hoisted(() => ({ stub: () => ({ default: { template: '<div />' } }) }))
vi.mock('@/components/stats/StatsGeneralTab.vue', stub)
vi.mock('@/components/stats/StatsUserProfilePopover.vue', stub)
vi.mock('@/components/stats/StatsMergeModal.vue', stub)
vi.mock('@/components/stats/StatsHoverPreview.vue', stub)

import StatsView from '@/views/StatsView.vue'

// What the app layout does: keep the view alive while another page is shown.
const Layout = {
  components: { StatsView, OtherPage: { template: '<div />' } },
  props: { onStats: Boolean },
  template: '<KeepAlive><StatsView v-if="onStats" /><OtherPage v-else /></KeepAlive>',
}

describe('StatsView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('polls only while the view is on screen', async () => {
    const wrapper = mount(Layout, { props: { onStats: true } })
    expect(startSessionPolling).toHaveBeenCalledTimes(1)
    expect(stopSessionPolling).not.toHaveBeenCalled()

    await wrapper.setProps({ onStats: false })
    expect(stopSessionPolling).toHaveBeenCalledTimes(1)

    await wrapper.setProps({ onStats: true })
    expect(startSessionPolling).toHaveBeenCalledTimes(2)

    wrapper.unmount()
    expect(stopSessionPolling).toHaveBeenCalledTimes(2)
  })
})
