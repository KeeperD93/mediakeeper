/**
 * An empty message shows no toast: the failure was already reported (the
 * rate-limit toast), so a caller's failure toast stays silent.
 */
import { describe, it, expect } from 'vitest'
import { useToast } from '@/composables/useToast'

describe('useToast', () => {
  it('shows nothing for an empty message', () => {
    const { toasts, showToast } = useToast()

    showToast('', 'err')
    expect(toasts.value).toHaveLength(0)

    showToast('Saved', 'ok', 0)
    expect(toasts.value.map(toast => toast.message)).toEqual(['Saved'])
  })
})
