/**
 * Cinema room playback poller — composable behavior.
 *
 * Mocks ``apiGet`` so we can assert:
 *   1. start() fires an immediate fetch + arms a 3 s interval;
 *   2. stop() clears the interval and flips ``enabled`` to false;
 *   3. an ``is_marathon=false`` payload no longer auto-stops the
 *      poller — single-film events surface their playback timer
 *      through the same poll, so it has to keep ticking.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiGetMock = vi.fn()
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: apiGetMock }),
}))

describe('useMarathonProgress', () => {
  beforeEach(() => {
    apiGetMock.mockReset()
    vi.useRealTimers()
  })

  it('start() fetches immediately and arms a 3 s interval', async () => {
    apiGetMock.mockResolvedValue({ is_marathon: true, ready: false, participants: [] })
    const { useMarathonProgress } = await import('@/composables/portal/useMarathonProgress')

    vi.useFakeTimers()
    const poll = useMarathonProgress(42)
    poll.start()
    await Promise.resolve()
    await Promise.resolve()

    expect(apiGetMock).toHaveBeenCalledTimes(1)
    expect(apiGetMock).toHaveBeenCalledWith('/api/portal/events/rooms/42/marathon-progress')
    expect(poll.enabled.value).toBe(true)

    vi.advanceTimersByTime(3000)
    expect(apiGetMock).toHaveBeenCalledTimes(2)

    poll.stop()
    expect(poll.enabled.value).toBe(false)
  })

  it('stop() clears the interval — no more polling after', async () => {
    apiGetMock.mockResolvedValue({ is_marathon: true, ready: false, participants: [] })
    const { useMarathonProgress } = await import('@/composables/portal/useMarathonProgress')

    vi.useFakeTimers()
    const poll = useMarathonProgress(7)
    poll.start()
    await Promise.resolve()
    poll.stop()
    apiGetMock.mockClear()
    vi.advanceTimersByTime(15000)

    expect(apiGetMock).not.toHaveBeenCalled()
  })

  it('keeps polling for single-film events (is_marathon=false)', async () => {
    // Single-film events now surface their playback timer through the
    // same payload — auto-stop would hide the timer past the first
    // tick, which is exactly the regression we just fixed.
    apiGetMock.mockResolvedValue({
      is_marathon: false,
      current_step: 0,
      ready: false,
      participants: [],
    })
    const { useMarathonProgress } = await import('@/composables/portal/useMarathonProgress')

    vi.useFakeTimers()
    const poll = useMarathonProgress(123)
    poll.start()
    await Promise.resolve()
    await Promise.resolve()

    expect(poll.enabled.value).toBe(true)
    apiGetMock.mockClear()
    vi.advanceTimersByTime(6000)
    // 6 s / 3 s interval → at least one more tick fired.
    expect(apiGetMock.mock.calls.length).toBeGreaterThan(0)
    poll.stop()
  })

  it('bump() forces an out-of-tick fetch', async () => {
    apiGetMock.mockResolvedValue({ is_marathon: true, ready: false, participants: [] })
    const { useMarathonProgress } = await import('@/composables/portal/useMarathonProgress')

    vi.useFakeTimers()
    const poll = useMarathonProgress(77)
    poll.start()
    await Promise.resolve()
    await Promise.resolve()
    apiGetMock.mockClear()

    poll.bump()
    await Promise.resolve()
    await Promise.resolve()
    expect(apiGetMock).toHaveBeenCalledTimes(1)
    poll.stop()
  })

  it('exposes ready as a computed mirroring progress.ready', async () => {
    apiGetMock.mockResolvedValue({ is_marathon: true, ready: true, participants: [] })
    const { useMarathonProgress } = await import('@/composables/portal/useMarathonProgress')

    const poll = useMarathonProgress(9)
    poll.start()
    await Promise.resolve()
    await Promise.resolve()
    expect(poll.ready.value).toBe(true)
    poll.stop()
  })
})
