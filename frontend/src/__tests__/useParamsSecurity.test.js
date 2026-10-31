/**
 * Settings > Security lists: both lists reload together after every action, a
 * failed load or action is said once (never a raw code), an older answer never
 * replaces a newer one, and the 15 s refresh stops when asked.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import { TOAST_TYPE } from '@/constants/toast'

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
  showToast: vi.fn(),
  confirm: vi.fn(),
}))
// Fake translations behind resolveApiError / resolveScopedError: an unknown key
// comes back unchanged, as with vue-i18n.
const MESSAGES = vi.hoisted(() => ({
  'settings.security.errors.invalid_ip': 'Not a valid IP address.',
  'settings.security.unblockFailed': 'Unblocking failed.',
  'settings.security.blockFailed': 'Blocking failed.',
  'settings.security.loadFailed': 'Could not load.',
}))
const t = (key, named) => key + (named ? JSON.stringify(named) : '')

vi.mock('@/i18n', () => ({
  default: { global: { t: key => MESSAGES[key] ?? key } },
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t, te: key => key.includes('.scopes.') }) }))
vi.mock('@/composables/useApi', async importOriginal => ({
  ...(await importOriginal()),
  useApi: () => ({ apiGet: mocks.apiGet, apiPost: mocks.apiPost, apiDelete: mocks.apiDelete }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => mocks.confirm }))

import { useParamsSecurity } from '@/composables/useParamsSecurity'

const BLOCKS = { items: [{ id: 7, ip: '203.0.113.5', scope: 'portal' }] }
const ATTEMPTS = { items: [{ id: 1, ip: '203.0.113.5', scope: 'portal', success: false }] }
const getUrls = () => mocks.apiGet.mock.calls.map(call => call[0])

function answerLists() {
  mocks.apiGet.mockImplementation(url =>
    Promise.resolve(url.startsWith('/api/security/blocks') ? BLOCKS : ATTEMPTS),
  )
}

describe('useParamsSecurity', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    answerLists()
    mocks.apiPost.mockResolvedValue({ id: 9 })
    mocks.apiDelete.mockResolvedValue({ success: true })
    mocks.confirm.mockResolvedValue(true)
  })
  afterEach(() => vi.useRealTimers())

  it('loads both lists, failures only by default', async () => {
    const s = useParamsSecurity()
    await s.refresh()

    expect(getUrls()).toEqual([
      '/api/security/blocks',
      '/api/security/attempts?limit=100&only_failures=true',
    ])
    expect(s.blocks.value).toEqual(BLOCKS.items)
    expect(s.attempts.value).toEqual(ATTEMPTS.items)
    expect(s.blocksLoaded.value && s.attemptsLoaded.value).toBe(true)
  })

  it('reloads the lists when the failures-only filter changes', async () => {
    const s = useParamsSecurity()
    s.onlyFailures.value = false
    await nextTick()
    await vi.waitFor(() =>
      expect(getUrls()).toContain('/api/security/attempts?limit=100&only_failures=false'),
    )
  })

  it('keeps the newest answer when an older one comes back last', async () => {
    const s = useParamsSecurity()
    let releaseOld
    mocks.apiGet.mockImplementation(url => {
      if (url.includes('only_failures=true')) {
        return new Promise(resolve => {
          releaseOld = () => resolve({ items: [{ id: 'old' }] })
        })
      }
      return Promise.resolve(
        url.startsWith('/api/security/blocks') ? BLOCKS : { items: [{ id: 'new' }] },
      )
    })
    const slow = s.refresh()
    s.onlyFailures.value = false
    await vi.waitFor(() => expect(s.attempts.value).toEqual([{ id: 'new' }]))
    releaseOld()
    await slow
    expect(s.attempts.value).toEqual([{ id: 'new' }])
  })

  it('says once that a list failed to load and keeps what was on screen', async () => {
    const s = useParamsSecurity()
    await s.refresh()
    mocks.apiGet.mockRejectedValue(new Error('Failed to fetch'))

    await s.refresh({ silent: true })
    await s.refresh({ silent: true })

    expect(mocks.showToast).toHaveBeenCalledTimes(1)
    expect(mocks.showToast).toHaveBeenCalledWith('Could not load.', TOAST_TYPE.ERR)
    expect(s.blocks.value).toEqual(BLOCKS.items)
    expect(s.blocksFailed.value).toBe(true)
  })

  it('ignores a refresh that a newer one replaced, then still reports an outage', async () => {
    const s = useParamsSecurity()
    const rejects = []
    mocks.apiGet.mockImplementation(
      () => new Promise((_, reject) => rejects.push(() => reject(new Error('http_504')))),
    )
    const older = s.refresh({ silent: true })
    answerLists()
    await s.refresh()
    rejects.forEach(reject => reject())
    await older

    expect(mocks.showToast).not.toHaveBeenCalled()
    expect(s.blocksFailed.value || s.attemptsFailed.value).toBe(false)

    mocks.apiGet.mockRejectedValue(new Error('http_504'))
    await s.refresh({ silent: true })
    expect(mocks.showToast).toHaveBeenCalledTimes(1)
  })

  it('does not repeat an outage when an older refresh succeeds late', async () => {
    const s = useParamsSecurity()
    const resolves = []
    mocks.apiGet.mockImplementation(
      () => new Promise(resolve => resolves.push(() => resolve({ items: [] }))),
    )
    const older = s.refresh({ silent: true })
    mocks.apiGet.mockRejectedValue(new Error('http_504'))
    await s.refresh({ silent: true })
    resolves.forEach(resolve => resolve())
    await older
    await s.refresh({ silent: true })

    expect(mocks.showToast).toHaveBeenCalledTimes(1)
  })

  it('marks a list unavailable when its first load fails', async () => {
    mocks.apiGet.mockRejectedValue(new Error('http_502'))
    const s = useParamsSecurity()
    await s.refresh()

    expect(s.blocksLoaded.value).toBe(false)
    expect(s.blocksFailed.value).toBe(true)
  })

  it('unblocks then reloads both lists', async () => {
    const s = useParamsSecurity()
    await s.unblock({ id: 7 })

    expect(mocks.apiDelete).toHaveBeenCalledWith('/api/security/blocks/7')
    expect(getUrls()).toEqual([
      '/api/security/blocks',
      '/api/security/attempts?limit=100&only_failures=true',
    ])
    expect(s.busy.value).toBe(false)
  })

  it('treats a block already gone as done, without an error', async () => {
    mocks.apiDelete.mockRejectedValue(new Error('block_not_found'))
    const s = useParamsSecurity()

    expect(await s.unblock({ id: 7 })).toBe(true)
    expect(mocks.showToast).not.toHaveBeenCalled()
    expect(getUrls()).toHaveLength(2)
  })

  it('names a refused block with its own text, else the action that failed', async () => {
    const s = useParamsSecurity()
    mocks.apiPost.mockRejectedValueOnce(new Error('invalid_ip'))
    expect(await s.addBlock({ ip: '203.0.113.0/24' })).toBe(false)
    mocks.apiPost.mockRejectedValueOnce(new Error('Failed to fetch'))
    expect(await s.addBlock({ ip: '203.0.113.9' })).toBe(false)

    expect(mocks.showToast.mock.calls).toEqual([
      ['Not a valid IP address.', TOAST_TYPE.ERR],
      ['Blocking failed.', TOAST_TYPE.ERR],
    ])
  })

  it('asks before blocking an address from the attempts, then blocks it for good', async () => {
    const s = useParamsSecurity()
    await s.blockAttemptIp({ ip: '203.0.113.5', scope: 'portal' })

    expect(mocks.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        variant: 'danger',
        message: expect.stringContaining('"ip":"203.0.113.5"'),
      }),
    )
    expect(mocks.apiPost).toHaveBeenCalledWith('/api/security/blocks', {
      ip: '203.0.113.5',
      username: null,
      scope: 'portal',
      permanent: true,
      reason: 'manual_from_attempts',
    })
  })

  it('sends nothing when the confirmation is refused', async () => {
    mocks.confirm.mockResolvedValue(false)
    const s = useParamsSecurity()

    expect(await s.blockAttemptIp({ ip: '203.0.113.5', scope: 'admin' })).toBe(false)
    expect(mocks.apiPost).not.toHaveBeenCalled()
  })

  it('refreshes every 15 s until stopped, and skips while the page is hidden', async () => {
    vi.useFakeTimers()
    const s = useParamsSecurity()
    s.startAutoRefresh()
    s.startAutoRefresh()

    await vi.advanceTimersByTimeAsync(15000)
    expect(mocks.apiGet).toHaveBeenCalledTimes(2)

    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    await vi.advanceTimersByTimeAsync(15000)
    expect(mocks.apiGet).toHaveBeenCalledTimes(2)
    hidden.mockRestore()

    s.stopAutoRefresh()
    await vi.advanceTimersByTimeAsync(45000)
    expect(mocks.apiGet).toHaveBeenCalledTimes(2)
  })

  it('labels scopes and reasons, and keeps a typed reason as is', () => {
    const s = useParamsSecurity()
    expect(s.scopeLabel('portal')).toBe('settings.security.scopes.portal')
    expect(s.reasonLabel('auto_block_bruteforce_ip:portal')).toBe(
      'settings.security.reasons.autoIp',
    )
    expect(s.reasonLabel('auto_block_bruteforce_username:admin')).toBe(
      'settings.security.reasons.autoName',
    )
    expect(s.reasonLabel('manual_from_attempts')).toBe('settings.security.reasons.fromAttempts')
    expect(s.reasonLabel('scanner seen on the router')).toBe('scanner seen on the router')
    expect(s.reasonLabel(null)).toBe('—')
    expect(s.displayIp('unknown')).toBe('settings.security.unknownAddress')
    expect(s.displayIp('::1')).toBe('settings.security.localAddress')
    expect(s.displayIp('203.0.113.5')).toBe('203.0.113.5')
  })
})
