/**
 * Users page, "Create an administrator": the window sends no role (the server
 * makes administrators only), explains the rule, and says why a creation failed,
 * whether the server refused it or the request itself failed.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
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
  resolveScopedError: (scope, code, fallbackKey) => (code ? `${scope}.${code}` : fallbackKey),
}))

import RuLocalCreateModal from '@/components/portal/admin/users/RuLocalCreateModal.vue'

async function submitted(answer) {
  createLocalUser.mockImplementation(answer)
  const w = mount(RuLocalCreateModal, { props: { open: true }, attachTo: document.body })
  await w.findAll('input[type="text"]')[0].setValue('second-admin')
  await w.get('input[type="password"]').setValue('Test-Pass-12345')
  await w.get('form').trigger('submit')
  await flushPromises()
  return w
}

function errorText(w) {
  const error = w.find('.ru-form-error')
  return error.exists() ? error.text() : ''
}

describe('RuLocalCreateModal', () => {
  beforeEach(() => {
    createLocalUser.mockReset()
  })

  it('explains the rule to the screen reader when the window opens', () => {
    const w = mount(RuLocalCreateModal, { props: { open: true } })
    const help = w.get('.ru-help')
    expect(help.text()).toBe('requestsAdmin.users.drawerLocal.help')
    expect(w.get('[role="dialog"]').attributes('aria-describedby')).toBe(help.attributes('id'))
    expect(w.find('select').exists()).toBe(false)
    w.unmount()
  })

  it('sends no role and reports the created account', async () => {
    const w = await submitted(async () => ({ ok: true, profile_id: 7, user_id: 9 }))
    const payload = createLocalUser.mock.calls[0][0]
    expect(payload).toMatchObject({ username: 'second-admin', password: 'Test-Pass-12345' })
    expect(payload).not.toHaveProperty('role')
    expect(w.emitted('created')).toEqual([[{ ok: true, profile_id: 7, user_id: 9 }]])
    w.unmount()
  })

  it('says why the server refused the name', async () => {
    const w = await submitted(async () => ({ error: 'not_admin_name' }))
    expect(errorText(w)).toBe('requestsAdmin.users.errors.not_admin_name')
    expect(w.emitted('created')).toBeUndefined()
    w.unmount()
  })

  it('says why when the request itself fails, and lets the admin try again', async () => {
    const quiet = vi.spyOn(console, 'error').mockImplementation(() => {})
    const w = await submitted(async () => {
      throw new Error('validation_failed')
    })
    expect(errorText(w)).toBe('requestsAdmin.users.errors.validation_failed')
    expect(w.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
    expect(w.emitted('created')).toBeUndefined()
    w.unmount()
    quiet.mockRestore()
  })

  it('stays silent when the session ended and the page leaves for the sign-in', async () => {
    const w = await submitted(async () => null)
    expect(errorText(w)).toBe('')
    expect(w.emitted('created')).toBeUndefined()
    w.unmount()
  })
})
