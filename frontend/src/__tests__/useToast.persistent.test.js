import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from '@/composables/useToast'

describe('useToast — a toast that stays until dismissed', () => {
  const { toasts, showToast, removeToast } = useToast()

  beforeEach(() => vi.useFakeTimers())

  afterEach(() => {
    toasts.value.forEach(toast => removeToast(toast.id))
    vi.useRealTimers()
  })

  it('tells it apart from a toast on a timer', () => {
    showToast('Stays', 'err', 0)
    showToast('Goes', 'ok')

    expect(toasts.value.map(toast => [toast.message, toast.persistent])).toEqual([
      ['Stays', true],
      ['Goes', false],
    ])
  })

  it('keeps it after every timer has run', () => {
    showToast('Stays', 'err', 0)
    showToast('Goes', 'ok')

    vi.runAllTimers()

    expect(toasts.value.map(toast => toast.message)).toEqual(['Stays'])
  })
})
