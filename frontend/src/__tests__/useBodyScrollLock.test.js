/** Windows that hand over to one another keep the page locked until the last one closes. */
import { afterEach, describe, expect, it } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'
import { useBodyScrollLock } from '@/composables/useBodyScrollLock'

function lockFor(active) {
  const scope = effectScope()
  scope.run(() => useBodyScrollLock(active))
  return scope
}

afterEach(() => {
  document.body.style.overflow = ''
})

describe('useBodyScrollLock', () => {
  it('locks while active and gives back what the page had', async () => {
    document.body.style.overflow = 'auto'
    const active = ref(true)
    const scope = lockFor(active)
    expect(document.body.style.overflow).toBe('hidden')

    active.value = false
    await nextTick()
    expect(document.body.style.overflow).toBe('auto')
    scope.stop()
  })

  it('stays locked when the next window opens before the first one goes', () => {
    const wizard = lockFor(ref(true))
    const digest = lockFor(ref(true))

    wizard.stop()
    expect(document.body.style.overflow).toBe('hidden')

    digest.stop()
    expect(document.body.style.overflow).toBe('')
  })
})
