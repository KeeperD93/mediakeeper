import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from '@/composables/useToast'

describe('useToast — each toast keeps its own duration', () => {
  const { toasts, showToast, removeToast } = useToast()

  beforeEach(() => vi.useFakeTimers())

  afterEach(() => {
    toasts.value.forEach(toast => removeToast(toast.id))
    vi.useRealTimers()
  })

  it('keeps 5 s by default and the given delay otherwise', () => {
    showToast('Default', 'ok')
    showToast('Longer', 'warn', 8000)

    expect(toasts.value.map(toast => [toast.message, toast.duration])).toEqual([
      ['Default', 5000],
      ['Longer', 8000],
    ])
  })
})
