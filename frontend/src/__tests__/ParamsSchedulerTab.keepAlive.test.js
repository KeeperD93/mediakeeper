/**
 * Settings > Scheduler inside SettingsView's KeepAlive: tasks and cache reload
 * each time the tab is shown, the refreshes run only while it is shown, and
 * nothing answering after the tab was left wakes them up.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineAsyncComponent, h, KeepAlive, nextTick, ref } from 'vue'

const apiGet = vi.hoisted(() => vi.fn())
const apiFetch = vi.hoisted(() => vi.fn())

vi.mock('@/i18n', () => ({ default: { global: { t: key => key } } }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key, te: () => false }) }))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiFetch }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const TASKS = '/api/scheduler/tasks'
const CACHES = '/api/scheduler/caches'
const TASKS_EVERY_MS = 2000
const CACHES_EVERY_MS = 5000
const LAUNCH_DELAY_MS = 1500
const LONG_AWAY_MS = 30000

const Other = { render: () => h('p', 'other tab') }
let SchedulerTab

function testTask(status) {
  return {
    key: 'test_task',
    label: 'Test task',
    enabled: true,
    interval_sec: 3600,
    last_status: status,
    run_count: 1,
  }
}

function serverSays(status) {
  apiGet.mockImplementation(async url => (url === TASKS ? [testTask(status)] : { items: [] }))
}

const callsTo = url => apiGet.mock.calls.filter(([called]) => called === url).length

async function mountHost() {
  const shown = ref(true)
  const Host = {
    setup: () => () => h(KeepAlive, null, [shown.value ? h(SchedulerTab) : h(Other)]),
  }
  const wrapper = mount(Host, { attachTo: document.body })
  await flushPromises()
  return { wrapper, shown }
}

async function show(shown, value) {
  shown.value = value
  await nextTick()
  await flushPromises()
}

const dotClasses = wrapper => wrapper.find('.str-dot').classes()

describe('ParamsSchedulerTab — kept alive by SettingsView', () => {
  beforeEach(async () => {
    apiGet.mockReset()
    apiFetch.mockReset()
    apiFetch.mockResolvedValue({ json: async () => ({ success: true }) })
    // The composable keeps its lists and timers at module level: each test starts anew.
    vi.resetModules()
    const { default: tab } = await import('@/components/settings/ParamsSchedulerTab.vue')
    SchedulerTab = defineAsyncComponent(() => Promise.resolve(tab))
    vi.useFakeTimers()
  })
  afterEach(() => vi.useRealTimers())

  it('loads tasks and cache on first display, then refreshes the cache alone', async () => {
    serverSays('ok')
    const { wrapper } = await mountHost()
    expect([callsTo(TASKS), callsTo(CACHES)]).toEqual([1, 1])

    await vi.advanceTimersByTimeAsync(CACHES_EVERY_MS)
    expect([callsTo(TASKS), callsTo(CACHES)]).toEqual([1, 2])
    wrapper.unmount()
  })

  it('stops refreshing while another tab is shown, reloads and resumes on return', async () => {
    serverSays('ok')
    const { wrapper, shown } = await mountHost()

    await show(shown, false)
    await vi.advanceTimersByTimeAsync(LONG_AWAY_MS)
    expect([callsTo(TASKS), callsTo(CACHES)]).toEqual([1, 1])

    await show(shown, true)
    expect([callsTo(TASKS), callsTo(CACHES)]).toEqual([2, 2])

    await vi.advanceTimersByTimeAsync(CACHES_EVERY_MS)
    expect(callsTo(CACHES)).toBe(3)
    wrapper.unmount()
  })

  it('shows on return that a task finished while the tab was away', async () => {
    serverSays('running')
    const { wrapper, shown } = await mountHost()
    expect(dotClasses(wrapper)).toContain('dot-running')

    await show(shown, false)
    serverSays('ok')
    await show(shown, true)

    expect(dotClasses(wrapper)).toContain('dot-ok')
    await vi.advanceTimersByTimeAsync(LONG_AWAY_MS)
    expect(callsTo(TASKS)).toBe(2)
    wrapper.unmount()
  })

  it('goes back to following a task still running on return', async () => {
    serverSays('ok')
    const { wrapper, shown } = await mountHost()

    await show(shown, false)
    serverSays('running')
    await show(shown, true)
    expect(callsTo(TASKS)).toBe(2)

    await vi.advanceTimersByTimeAsync(TASKS_EVERY_MS)
    expect(callsTo(TASKS)).toBe(3)
    wrapper.unmount()
  })

  it('keeps the cache moving once a followed task finishes', async () => {
    serverSays('running')
    const { wrapper } = await mountHost()

    serverSays('ok')
    await vi.advanceTimersByTimeAsync(TASKS_EVERY_MS)
    expect(callsTo(TASKS)).toBe(2)

    const cacheCalls = callsTo(CACHES)
    await vi.advanceTimersByTimeAsync(CACHES_EVERY_MS)
    expect(callsTo(CACHES)).toBe(cacheCalls + 1)
    expect(callsTo(TASKS)).toBe(2)
    wrapper.unmount()
  })

  it('stays asleep when a load answers after the tab was left', async () => {
    let answerTasks
    apiGet.mockImplementation(url =>
      url === TASKS
        ? new Promise(resolve => {
            answerTasks = resolve
          })
        : Promise.resolve({ items: [] }),
    )
    const { wrapper, shown } = await mountHost()

    await show(shown, false)
    answerTasks([testTask('running')])
    await flushPromises()

    await vi.advanceTimersByTimeAsync(LONG_AWAY_MS)
    expect(callsTo(TASKS)).toBe(1)
    wrapper.unmount()
  })

  it('follows a task launched while shown', async () => {
    serverSays('ok')
    const { wrapper } = await mountHost()

    await wrapper.find('.str-run-btn').trigger('click')
    await flushPromises()
    serverSays('running')

    await vi.advanceTimersByTimeAsync(LAUNCH_DELAY_MS)
    expect(callsTo(TASKS)).toBe(2)
    await vi.advanceTimersByTimeAsync(TASKS_EVERY_MS)
    expect(callsTo(TASKS)).toBe(3)
    wrapper.unmount()
  })

  it('stays asleep when a task was launched just before the tab was left', async () => {
    serverSays('ok')
    const { wrapper, shown } = await mountHost()

    await wrapper.find('.str-run-btn').trigger('click')
    await flushPromises()
    await show(shown, false)
    serverSays('running')

    await vi.advanceTimersByTimeAsync(LAUNCH_DELAY_MS)
    const tasksCalls = callsTo(TASKS)
    await vi.advanceTimersByTimeAsync(LONG_AWAY_MS)
    expect(callsTo(TASKS)).toBe(tasksCalls)
    wrapper.unmount()
  })

  it('keeps an interval typed but not saved across a return', async () => {
    serverSays('ok')
    const { wrapper, shown } = await mountHost()
    await wrapper.find('.str-interval-amount').setValue('5')

    await show(shown, false)
    await show(shown, true)

    expect(wrapper.find('.str-interval-amount').element.value).toBe('5')
    expect(wrapper.find('.str-save-btn').exists()).toBe(true)
    wrapper.unmount()
  })

  it('keeps the lists on screen during the reload on return', async () => {
    apiGet.mockImplementation(async url =>
      url === TASKS
        ? [testTask('ok')]
        : { items: [{ id: 'test', name: 'Test cache', ttl_seconds: 60 }] },
    )
    const { wrapper, shown } = await mountHost()

    await show(shown, false)
    apiGet.mockImplementation(() => new Promise(() => {}))
    await show(shown, true)

    expect(wrapper.find('.str-row').exists()).toBe(true)
    expect(wrapper.find('.scl-name').exists()).toBe(true)
    expect(wrapper.find('.stl-skel').exists()).toBe(false)
    expect(wrapper.find('.scl-skel').exists()).toBe(false)
    wrapper.unmount()
  })

  it('reloads the tasks when coming back from another page', async () => {
    serverSays('running')
    const first = await mountHost()
    first.wrapper.unmount()

    serverSays('ok')
    const { wrapper } = await mountHost()

    expect(callsTo(TASKS)).toBe(2)
    expect(dotClasses(wrapper)).toContain('dot-ok')
    wrapper.unmount()
  })

  it('stops refreshing once unmounted', async () => {
    serverSays('running')
    const { wrapper } = await mountHost()

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(LONG_AWAY_MS)
    expect([callsTo(TASKS), callsTo(CACHES)]).toEqual([1, 1])
  })
})
