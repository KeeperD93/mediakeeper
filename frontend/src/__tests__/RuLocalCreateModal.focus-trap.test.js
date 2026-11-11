/**
 * Covers useFocusTrap wired into RuLocalCreateModal: one initial focus, on the
 * close button, and Escape routing through the close handler, which waits for a
 * creation in flight.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const createLocalUser = vi.fn()

vi.mock('lucide-vue-next', () => ({
  Eye: { name: 'EyeStub', template: '<i />' },
  EyeOff: { name: 'EyeOffStub', template: '<i />' },
  X: { name: 'XStub', template: '<i />' },
}))
vi.mock('@/composables/portal/usePortalAdminUsers', () => ({
  usePortalAdminUsers: () => ({ createLocalUser }),
}))
vi.mock('@/composables/useApi', () => ({
  resolveScopedError: (_scope, _code, fallbackKey) => fallbackKey,
}))

import RuLocalCreateModal from '@/components/portal/admin/users/RuLocalCreateModal.vue'

function buildModal() {
  return mount(RuLocalCreateModal, { props: { open: true }, attachTo: document.body })
}

function pressEscape() {
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
}

describe('RuLocalCreateModal — focus trap integration', () => {
  it('moves initial focus onto the close button, and only there', async () => {
    const w = buildModal()
    await flushPromises()

    expect(document.activeElement).toBe(w.get('.atl-close').element)
    expect(w.find('[autofocus]').exists()).toBe(false)

    w.unmount()
  })

  it('routes Escape to the close handler and emits close exactly once', async () => {
    const w = buildModal()
    await flushPromises()

    pressEscape()
    await flushPromises()

    expect(w.emitted('close')).toHaveLength(1)

    w.unmount()
  })

  it('keeps the window open on Escape while a creation is in flight', async () => {
    let answer
    createLocalUser.mockImplementation(() => new Promise(resolve => (answer = resolve)))
    const w = buildModal()
    await flushPromises()
    await w.get('form').trigger('submit')

    pressEscape()
    await flushPromises()
    expect(w.emitted('close')).toBeUndefined()

    answer({ ok: true, profile_id: 7, user_id: 9 })
    await flushPromises()
    w.unmount()
  })
})
