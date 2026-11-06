/**
 * Portal admin → debug tools: the player picker reads its labels from the translations,
 * and a list that fails to load says so.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const listUsers = vi.fn()
const listAchievements = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/portal/usePortalAdminDebug', () => ({
  usePortalAdminDebug: () => ({ listUsers, listAchievements }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key, named) => (named ? `${key}=${named.n}` : key) }),
}))
vi.mock('@/i18n', () => ({ getLocale: () => 'en' }))

import AdminDebug from '@/components/portal/admin/AdminDebug.vue'
import { TOAST_TYPE } from '@/constants/toast'

const USERS = [
  { user_id: 1, display_name: 'Alice', role: 'admin', level: 2, xp: 1300 },
  { user_id: 2, display_name: 'Bob', role: 'viewer', level: 0, xp: 0 },
]

async function mountPage() {
  const wrapper = mount(AdminDebug, {
    global: { stubs: { AdminDebugBulkTools: true } },
  })
  await flushPromises()
  return wrapper
}

describe('AdminDebug', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listAchievements.mockResolvedValue([])
  })

  it('labels each player with translated level and XP, and marks the admins', async () => {
    listUsers.mockResolvedValue(USERS)
    const options = (await mountPage()).findAll('option').map(o => o.text())
    expect(options).toContain(
      'Alice · common.administrator · portal.admin.debug.level=2 · portal.admin.debug.xp=1,300',
    )
    expect(options).toContain('Bob · portal.admin.debug.level=0 · portal.admin.debug.xp=0')
  })

  it('says so when the player list fails to load', async () => {
    listUsers.mockRejectedValue(new Error('http_500'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    await mountPage()
    expect(showToast).toHaveBeenCalledWith('portal.admin.debug.errorGeneric', TOAST_TYPE.ERR)
  })
})
