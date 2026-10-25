/**
 * Settings > Security inside SettingsView's KeepAlive: the lists load each
 * time the tab is shown, the 15 s refresh runs only while it is shown, and
 * the add-block dialog (rendered on <body>) closes when the tab is left.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineAsyncComponent, defineComponent, h, KeepAlive, nextTick, ref } from 'vue'

const apiGet = vi.hoisted(() => vi.fn())

vi.mock('@/i18n', () => ({ default: { global: { t: key => key } } }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key, te: () => false }) }))
vi.mock('@/composables/useApi', async importOriginal => ({
  ...(await importOriginal()),
  useApi: () => ({ apiGet, apiPost: vi.fn(), apiDelete: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => async () => true }))
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ user: ref({ username: 'admin' }), changePassword: vi.fn() }),
}))

const Other = defineComponent({ render: () => h('p', 'other tab') })
const SecurityTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsSecurityTab.vue'),
)

function mountHost() {
  const showSecurity = ref(true)
  const Host = defineComponent({
    setup: () => () => h(KeepAlive, null, [showSecurity.value ? h(SecurityTab) : h(Other)]),
  })
  // The real Teleport: its children stay on <body> when KeepAlive hides the tab.
  const wrapper = mount(Host, { attachTo: document.body, global: { stubs: { Teleport: false } } })
  return { wrapper, showSecurity }
}

describe('ParamsSecurityTab — kept alive by SettingsView', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    apiGet.mockReset()
    apiGet.mockResolvedValue({ items: [] })
  })
  afterEach(() => vi.useRealTimers())

  it('loads both lists on first display, then every 15 s while shown', async () => {
    const { wrapper } = mountHost()
    await vi.waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2))

    await vi.advanceTimersByTimeAsync(15000)
    expect(apiGet).toHaveBeenCalledTimes(4)
    wrapper.unmount()
  })

  it('stops refreshing while another tab is shown and reloads on return', async () => {
    const { wrapper, showSecurity } = mountHost()
    await vi.waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2))

    showSecurity.value = false
    await nextTick()
    await vi.advanceTimersByTimeAsync(45000)
    expect(apiGet).toHaveBeenCalledTimes(2)

    showSecurity.value = true
    await nextTick()
    await flushPromises()
    expect(apiGet).toHaveBeenCalledTimes(4)
    wrapper.unmount()
  })

  it('stops refreshing once unmounted', async () => {
    const { wrapper } = mountHost()
    await vi.waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2))

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(45000)
    expect(apiGet).toHaveBeenCalledTimes(2)
  })

  it('keeps the table on screen during a refresh', async () => {
    apiGet.mockResolvedValue({ items: [{ id: 1, ip: '203.0.113.5', scope: 'portal' }] })
    const { wrapper } = mountHost()
    await vi.waitFor(() => expect(wrapper.findAll('table')).toHaveLength(2))

    apiGet.mockReturnValue(new Promise(() => {}))
    await wrapper
      .findAll('button')
      .find(b => b.text() === 'common.refresh')
      .trigger('click')
    expect(wrapper.findAll('table')).toHaveLength(2)
    expect(wrapper.text()).not.toContain('common.loading')
    wrapper.unmount()
  })

  it('closes the add-block dialog when the tab is left', async () => {
    const { wrapper, showSecurity } = mountHost()
    await vi.waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2))

    const add = wrapper.findAll('button').find(b => b.text() === 'settings.security.addBlock')
    await add.trigger('click')
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()

    showSecurity.value = false
    await nextTick()
    await flushPromises()
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    wrapper.unmount()
  })
})
