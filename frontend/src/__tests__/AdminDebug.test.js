/**
 * Portal admin → debug tools: the player picker reads its labels from the translations,
 * a list that fails to load says so, and the level field sends only the server's bounds.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const listUsers = vi.fn()
const listAchievements = vi.fn()
const setLevel = vi.fn()
const grantXp = vi.fn()
const unlockAchievement = vi.fn()
const lockAchievement = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/portal/usePortalAdminDebug', () => ({
  usePortalAdminDebug: () => ({
    listUsers,
    listAchievements,
    setLevel,
    grantXp,
    unlockAchievement,
    lockAchievement,
  }),
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
  { user_id: 2, display_name: 'Bob', role: 'viewer', level: 1, xp: 0 },
]

async function mountPage() {
  const wrapper = mount(AdminDebug, {
    global: { stubs: { AdminDebugBulkTools: true, AdminDebugZoneCorrection: true } },
  })
  await flushPromises()
  return wrapper
}

async function mountWithBob() {
  listUsers.mockResolvedValue(USERS)
  const wrapper = await mountPage()
  await wrapper.findAll('select')[0].setValue(2)
  return wrapper
}

const buttonOf = (wrapper, key) =>
  wrapper.findAll('button').find(b => b.text() === `portal.admin.debug.${key}`)

// Picks Bob, then returns the level field and its button.
async function mountLevelTool() {
  const wrapper = await mountWithBob()
  const input = wrapper.find('input[placeholder="portal.admin.debug.levelTarget"]')
  return { input, button: buttonOf(wrapper, 'levelApply') }
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
    expect(options).toContain('Bob · portal.admin.debug.level=1 · portal.admin.debug.xp=0')
  })

  it('sends only whole levels from 1 to 50, like the server', async () => {
    setLevel.mockResolvedValue({ xp: 0, level: 1 })
    const { input, button } = await mountLevelTool()
    expect(input.attributes('min')).toBe('1')
    expect(input.attributes('max')).toBe('50')

    for (const typed of ['0', '-4', '51', '1.5', '']) {
      await input.setValue(typed)
      expect(button.attributes('disabled'), typed).toBeDefined()
      await button.trigger('click')
    }
    expect(setLevel).not.toHaveBeenCalled()

    for (const level of [1, 50]) {
      await input.setValue(String(level))
      expect(button.attributes('disabled')).toBeUndefined()
      await button.trigger('click')
      await flushPromises()
      expect(setLevel).toHaveBeenLastCalledWith(2, level)
    }
  })

  it('logs a failed level change and says so', async () => {
    const failure = new Error('http_500')
    setLevel.mockRejectedValue(failure)
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { input, button } = await mountLevelTool()
    await input.setValue('3')
    await button.trigger('click')
    await flushPromises()
    expect(consoleError).toHaveBeenCalledWith('[AdminDebug.applyLevel]', failure)
    expect(showToast).toHaveBeenCalledWith('portal.admin.debug.errorGeneric', TOAST_TYPE.ERR)
  })

  it('logs the failures of the XP and trophy actions', async () => {
    const failure = new Error('http_500')
    for (const call of [grantXp, unlockAchievement, lockAchievement]) {
      call.mockRejectedValue(failure)
    }
    listAchievements.mockResolvedValue([
      { id: 'test_trophy', name_key: 'test.trophy', category: 'watch', tier: 1 },
    ])
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await mountWithBob()
    await wrapper.find('input[placeholder="portal.admin.debug.xpAmount"]').setValue('10')
    for (const key of ['xpApply', 'achievementUnlock', 'achievementLock']) {
      await buttonOf(wrapper, key).trigger('click')
    }
    await flushPromises()
    for (const action of ['applyXp', 'unlockAch', 'lockAch']) {
      expect(consoleError).toHaveBeenCalledWith(`[AdminDebug.${action}]`, failure)
    }
  })

  it('says so when the player list fails to load', async () => {
    listUsers.mockRejectedValue(new Error('http_500'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    await mountPage()
    expect(showToast).toHaveBeenCalledWith('portal.admin.debug.errorGeneric', TOAST_TYPE.ERR)
  })
})
