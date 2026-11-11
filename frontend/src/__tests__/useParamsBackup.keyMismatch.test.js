/**
 * A restore refused for its encryption key gives steps to follow: the message
 * stays on screen until dismissed, and nothing claims a restore happened.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BACKUP_KEY_MISMATCH } from '@/constants/backup'
import { TOAST_TYPE } from '@/constants/toast'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  showToast: vi.fn(),
  t: vi.fn(key => key),
}))
const REFUSED = vi.hoisted(() => 'Restore refused.')

vi.mock('@/i18n', () => ({
  default: {
    global: { t: key => (key === 'common.apiError.backup_key_mismatch' ? REFUSED : key) },
  },
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: mocks.t }) }))
vi.mock('@/composables/useApi', async importOriginal => ({
  ...(await importOriginal()),
  useApi: () => ({ apiFetch: mocks.apiFetch, apiGet: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => async () => true }))

import { useParamsBackup } from '@/composables/useParamsBackup'

describe('useParamsBackup — restore refused for its encryption key', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.apiFetch.mockRejectedValue(new Error(BACKUP_KEY_MISMATCH))
  })

  it('keeps the message until dismissed after a restore from the list', async () => {
    await useParamsBackup().restoreBackup('mediakeeper_backup_x.zip')

    expect(mocks.showToast.mock.calls).toEqual([[REFUSED, TOAST_TYPE.ERR, 0]])
  })

  it('does the same after an upload and clears the file input', async () => {
    const event = { target: { files: [new File(['x'], 'backup.zip')], value: 'backup.zip' } }

    await useParamsBackup().uploadRestore(event)

    expect(mocks.showToast.mock.calls).toEqual([[REFUSED, TOAST_TYPE.ERR, 0]])
    expect(event.target.value).toBe('')
  })

  it('has its message in both languages', () => {
    expect(fr.common.apiError[BACKUP_KEY_MISMATCH]).toBeTruthy()
    expect(en.common.apiError[BACKUP_KEY_MISMATCH]).toBeTruthy()
  })
})

describe('useParamsBackup — restore that skipped unreadable secrets', () => {
  const answer = results => ({ json: async () => ({ success: true, results }) })

  beforeEach(() => vi.clearAllMocks())

  it('says how many were skipped', async () => {
    mocks.apiFetch.mockResolvedValue(answer({ settings: 'ok', secrets_skipped: 2 }))

    await useParamsBackup().restoreBackup('mediakeeper_backup_x.zip')

    expect(mocks.t).toHaveBeenCalledWith('backup.restoreSecretsSkipped', { n: 2 }, 2)
    expect(mocks.showToast).toHaveBeenCalledWith(
      'backup.restoreSecretsSkipped',
      TOAST_TYPE.WARN,
      10000,
    )
  })

  it('stays silent when none was skipped', async () => {
    mocks.apiFetch.mockResolvedValue(answer({ settings: 'ok' }))

    await useParamsBackup().restoreBackup('mediakeeper_backup_x.zip')

    expect(mocks.t).not.toHaveBeenCalledWith(
      'backup.restoreSecretsSkipped',
      expect.anything(),
      expect.anything(),
    )
  })

  it('words one and several in both languages, with the real plural rules', async () => {
    const { createI18n } = await vi.importActual('vue-i18n')
    const cases = [
      ['fr', fr, /^1 secret illisible/, /^3 secrets illisibles/],
      ['en', en, /^1 unreadable secret/, /^3 unreadable secrets/],
    ]
    for (const [locale, messages, one, several] of cases) {
      const { t } = createI18n({ legacy: false, locale, messages: { [locale]: messages } }).global
      expect(t('backup.restoreSecretsSkipped', { n: 1 }, 1)).toMatch(one)
      expect(t('backup.restoreSecretsSkipped', { n: 3 }, 3)).toMatch(several)
    }
  })
})
