import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useBackendHealth } from '@/composables/useBackendHealth'

function makeRouter({ name = 'home' } = {}) {
  return {
    currentRoute: ref({ name }),
    push: vi.fn().mockResolvedValue(undefined),
  }
}

function jsonResponse(body) {
  return { ok: true, json: () => Promise.resolve(body) }
}

function makeDeps(overrides = {}) {
  const router = overrides.router ?? makeRouter()
  return {
    fetchApiResponse: overrides.fetchApiResponse ?? vi.fn(),
    router,
    logout: overrides.logout ?? vi.fn().mockResolvedValue(undefined),
    showToast: overrides.showToast ?? vi.fn(),
    t: overrides.t ?? (key => key),
    reload: overrides.reload ?? vi.fn(),
    setInterval: overrides.setInterval ?? vi.fn(() => 1),
    clearInterval: overrides.clearInterval ?? vi.fn(),
  }
}

describe('useBackendHealth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initial state: not down, no boot id stored', () => {
    const deps = makeDeps()
    const h = useBackendHealth(deps)
    expect(h.backendDown.value).toBe(false)
  })

  it('skips polling on /login route', async () => {
    const router = makeRouter({ name: 'login' })
    const fetchApiResponse = vi.fn()
    const deps = makeDeps({ router, fetchApiResponse })
    const h = useBackendHealth(deps)
    await h.tick()
    expect(fetchApiResponse).not.toHaveBeenCalled()
    expect(h.backendDown.value).toBe(false)
  })

  it('flips backendDown=true after 3 consecutive failures', async () => {
    const fetchApiResponse = vi.fn().mockResolvedValue({ ok: false })
    const deps = makeDeps({ fetchApiResponse })
    const h = useBackendHealth(deps)

    await h.tick()
    expect(h.backendDown.value).toBe(false)
    await h.tick()
    expect(h.backendDown.value).toBe(false)
    await h.tick()
    expect(h.backendDown.value).toBe(true)
  })

  it('treats network exceptions as failures', async () => {
    const fetchApiResponse = vi.fn().mockRejectedValue(new Error('offline'))
    const deps = makeDeps({ fetchApiResponse })
    const h = useBackendHealth(deps)

    await h.tick()
    await h.tick()
    await h.tick()
    expect(h.backendDown.value).toBe(true)
  })

  it('reloads the page on reconnect when boot_id is unchanged', async () => {
    const fetchApiResponse = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok', boot_id: 'AAA' })) // first ok → store
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce(jsonResponse({ status: 'ok', boot_id: 'AAA' })) // reconnect

    const reload = vi.fn()
    const logout = vi.fn().mockResolvedValue(undefined)
    const deps = makeDeps({ fetchApiResponse, reload, logout })
    const h = useBackendHealth(deps)

    await h.tick() // first success — known boot
    await h.tick()
    await h.tick()
    await h.tick()
    expect(h.backendDown.value).toBe(true)
    await h.tick() // reconnect, same boot
    expect(reload).toHaveBeenCalledTimes(1)
    expect(logout).not.toHaveBeenCalled()
    expect(h.backendDown.value).toBe(false)
  })

  it('logs out + redirects when boot_id changes (rebuild detected)', async () => {
    const fetchApiResponse = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok', boot_id: 'AAA' }))
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce(jsonResponse({ status: 'ok', boot_id: 'BBB' }))

    const logout = vi.fn().mockResolvedValue(undefined)
    const router = makeRouter()
    const showToast = vi.fn()
    const reload = vi.fn()
    const deps = makeDeps({ fetchApiResponse, logout, router, showToast, reload })
    const h = useBackendHealth(deps)

    await h.tick()
    await h.tick()
    await h.tick()
    await h.tick()
    expect(h.backendDown.value).toBe(true)
    await h.tick()
    expect(logout).toHaveBeenCalledTimes(1)
    expect(router.push).toHaveBeenCalledWith('/login')
    expect(showToast).toHaveBeenCalledWith('app.rebuilt_logout', 'info')
    expect(reload).not.toHaveBeenCalled()
    expect(h.backendDown.value).toBe(false)
  })

  it('falls back to reload when the response carries no boot_id (legacy backend)', async () => {
    const fetchApiResponse = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' })) // no boot_id
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' })) // still no boot_id

    const reload = vi.fn()
    const logout = vi.fn()
    const deps = makeDeps({ fetchApiResponse, reload, logout })
    const h = useBackendHealth(deps)

    await h.tick()
    await h.tick()
    await h.tick()
    await h.tick()
    expect(h.backendDown.value).toBe(true)
    await h.tick()
    expect(reload).toHaveBeenCalledTimes(1)
    expect(logout).not.toHaveBeenCalled()
  })

  it('memorises boot_id arriving on the recovery tick when no prior value was known', async () => {
    const fetchApiResponse = vi
      .fn()
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce(jsonResponse({ status: 'ok', boot_id: 'FIRST' }))

    const reload = vi.fn()
    const logout = vi.fn()
    const deps = makeDeps({ fetchApiResponse, reload, logout })
    const h = useBackendHealth(deps)

    await h.tick()
    await h.tick()
    await h.tick()
    expect(h.backendDown.value).toBe(true)
    await h.tick()
    expect(reload).toHaveBeenCalledTimes(1)
    expect(logout).not.toHaveBeenCalled()
    expect(h.backendDown.value).toBe(false)
  })

  it('start/stop control the polling timer', () => {
    const setIntervalFn = vi.fn(() => 42)
    const clearIntervalFn = vi.fn()
    const deps = makeDeps({ setInterval: setIntervalFn, clearInterval: clearIntervalFn })
    const h = useBackendHealth(deps)

    h.start()
    expect(setIntervalFn).toHaveBeenCalledTimes(1)
    h.start()
    expect(setIntervalFn).toHaveBeenCalledTimes(1)
    h.stop()
    expect(clearIntervalFn).toHaveBeenCalledWith(42)
  })
})
