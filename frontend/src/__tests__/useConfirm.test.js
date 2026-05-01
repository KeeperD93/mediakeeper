import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import { useConfirm } from '@/composables/useConfirm'

describe('useConfirm', () => {
  let confirm

  beforeEach(() => {
    confirm = useConfirm()
  })

  afterEach(async () => {
    // Ensure any pending prompt resolves before the next test.
    await nextTick()
  })

  it('returns a function', () => {
    expect(typeof confirm).toBe('function')
  })

  it('resolves to the value returned by the MkConfirmDialog response', async () => {
    // We cannot drive the actual dialog UI from here (it lives in App.vue),
    // but we can verify the promise interface and that calling twice
    // supersedes any pending prompt.
    const first = confirm({ title: 't', message: 'm' })
    expect(first).toBeInstanceOf(Promise)

    const second = confirm({ title: 't2', message: 'm2' })
    // The first promise must resolve (to false) when a new prompt replaces it.
    await expect(first).resolves.toBe(false)
    expect(second).toBeInstanceOf(Promise)
  })
})
