/**
 * Cinema room marathon poller — composable behavior.
 *
 * Mocks ``apiGet`` so we can assert:
 *   1. start() fires an immediate fetch + arms an interval;
 *   2. stop() clears the interval and flips ``enabled`` to false;
 *   3. ``is_marathon=false`` payload auto-stops the poller.
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

  it('start() fetches immediately and arms a 5 s interval', async () => {
    apiGetMock.mockResolvedValue({ is_marathon: true, ready: false, participants: [] })
    const { useMarathonProgress } = await import('@/composables/portal/useMarathonProgress')

    vi.useFakeTimers()
    const poll = useMarathonProgress(42)
    poll.start()
    await Promise.resolve()
    await Promise.resolve()

    expect(apiGetMock).toHaveBeenCalledTimes(1)
    expect(apiGetMock).toHaveBeenCalledWith(
      '/api/portal/events/rooms/42/marathon-progress',
    )
    expect(poll.enabled.value).toBe(true)

    vi.advanceTimersByTime(5000)
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

  it('auto-stops the poller when the server says is_marathon=false', async () => {
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

    expect(poll.enabled.value).toBe(false)
    apiGetMock.mockClear()
    vi.advanceTimersByTime(20000)
    expect(apiGetMock).not.toHaveBeenCalled()
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
