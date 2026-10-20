/**
 * One confirmation on screen at a time: another one asked meanwhile waits
 * its turn instead of cancelling it, and the same one asked again (a double
 * click) is answered "no" at once. A waiting prompt cannot be accepted the
 * instant it appears, so a double click never answers it unread.
 */
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { QUEUED_PROMPT_GUARD_MS, useConfirm, _useConfirmState } from '@/composables/useConfirm'

const confirm = useConfirm()
const { state, accept, cancel } = _useConfirmState()

// Shows the waiting prompt and lets its guard run out.
async function showNext() {
  await nextTick()
  vi.advanceTimersByTime(QUEUED_PROMPT_GUARD_MS)
}

describe('useConfirm', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(async () => {
    while (state.value.open) {
      cancel()
      await nextTick()
    }
    vi.useRealTimers()
  })

  it('returns a promise', () => {
    const prompt = confirm({ title: 'Anything?' })

    expect(prompt).toBeInstanceOf(Promise)
  })

  it('lets a second prompt wait for the first to be answered', async () => {
    const deleteRowB = confirm({ title: 'Delete B?', variant: 'danger' })
    const forceRowA = confirm({ title: 'Mark A available anyway?', variant: 'warn' })
    expect(state.value.title).toBe('Delete B?')

    accept()
    expect(await deleteRowB).toBe(true)
    await showNext()
    expect(state.value).toMatchObject({ open: true, title: 'Mark A available anyway?' })

    cancel()
    expect(await forceRowA).toBe(false)
    expect(state.value.open).toBe(false)
  })

  it('answers "no" at once to the same prompt asked twice', async () => {
    const first = confirm({ title: 'Delete?', variant: 'danger' })
    expect(await confirm({ title: 'Delete?', variant: 'danger' })).toBe(false)

    accept()
    expect(await first).toBe(true)
  })

  it('ignores a double click that would accept the waiting prompt unread', async () => {
    const first = confirm({ title: 'Delete B?', variant: 'danger' })
    let secondAnswer = null
    confirm({ title: 'Mark A available anyway?', variant: 'warn' }).then(v => {
      secondAnswer = v
    })

    accept()
    await first
    await nextTick()
    accept() // second click of the double click
    await nextTick()

    expect(state.value).toMatchObject({ open: true, title: 'Mark A available anyway?' })
    expect(secondAnswer).toBeNull()

    vi.advanceTimersByTime(QUEUED_PROMPT_GUARD_MS)
    accept()
    await nextTick()
    expect(secondAnswer).toBe(true)
  })

  it('queues a prompt asked by the caller that was just answered', async () => {
    const first = confirm({ title: 'First?' })
    const second = confirm({ title: 'Second?' })

    accept()
    await first
    const third = confirm({ title: 'Third?' })
    await showNext()
    expect(state.value.title).toBe('Second?')

    accept()
    expect(await second).toBe(true)
    await showNext()
    expect(state.value.title).toBe('Third?')
    accept()
    expect(await third).toBe(true)
  })
})
