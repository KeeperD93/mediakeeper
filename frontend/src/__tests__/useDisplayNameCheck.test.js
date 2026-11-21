/** The live check of a display name: one request per pause, old answers ignored. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { useDisplayNameCheck } from '@/composables/portal/useDisplayNameCheck'
import { NAME_CHECK_FAILED } from '@/constants/portalOnboarding'

const apiGet = vi.fn()
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet }) }))

let scope
function checker() {
  scope = effectScope()
  return scope.run(() => useDisplayNameCheck())
}

// Answers kept pending until the test settles them, in any order.
function deferredAnswers() {
  const pending = []
  apiGet.mockImplementation(
    url =>
      new Promise(resolve => {
        pending.push({ name: decodeURIComponent(url.split('name=')[1]), resolve })
      }),
  )
  return pending
}

beforeEach(() => {
  vi.useFakeTimers()
  apiGet.mockReset()
})
afterEach(() => {
  scope?.stop()
  vi.useRealTimers()
})

describe('useDisplayNameCheck', () => {
  it('asks once, after the pause in typing', async () => {
    apiGet.mockResolvedValue({ reason: 'free', available: true, suggestions: [] })
    const { state, check } = checker()

    check('Bo')
    check('Bob')
    expect(state.pending).toBe(true)
    await vi.advanceTimersByTimeAsync(400)

    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiGet).toHaveBeenCalledWith('/api/portal/profiles/me/check-username?name=Bob')
    expect(state).toMatchObject({ name: 'Bob', pending: false, reason: 'free' })
  })

  it('ignores an answer about a name typed before', async () => {
    const pending = deferredAnswers()
    const { state, check } = checker()

    check('Bob')
    await vi.advanceTimersByTimeAsync(400)
    check('Bobby')
    await vi.advanceTimersByTimeAsync(400)
    pending[1].resolve({ reason: 'free', available: true })
    await vi.advanceTimersByTimeAsync(0)
    pending[0].resolve({ reason: 'taken', suggestions: ['Bob2'] })
    await vi.advanceTimersByTimeAsync(0)

    expect(state).toMatchObject({ name: 'Bobby', pending: false, reason: 'free', suggestions: [] })
  })

  it('says when no answer came, and asks nothing for an empty field', async () => {
    apiGet.mockRejectedValue(new Error('http_429'))
    const { state, check } = checker()

    check('Bob')
    await vi.advanceTimersByTimeAsync(400)
    expect(state.reason).toBe(NAME_CHECK_FAILED)

    check('   ')
    await vi.advanceTimersByTimeAsync(400)
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(state).toMatchObject({ name: '', pending: false, reason: null })
  })

  it('shows a refusal of the save as a verdict, dropping a check under way', async () => {
    const pending = deferredAnswers()
    const { state, check, refuse } = checker()

    check('Bob')
    await vi.advanceTimersByTimeAsync(400)
    refuse('Bob', 'reserved')
    pending[0].resolve({ reason: 'free', available: true })
    await vi.advanceTimersByTimeAsync(0)

    expect(state).toMatchObject({ pending: false, reason: 'reserved' })
  })
})
