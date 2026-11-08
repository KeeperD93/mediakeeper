/**
 * A restore refused for its encryption key gives steps to follow: the message
 * stays on screen until dismissed, and nothing claims a restore happened.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BACKUP_KEY_MISMATCH } from '@/constants/backup'
import { TOAST_TYPE } from '@/constants/toast'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), showToast: vi.fn() }))
const REFUSED = vi.hoisted(() => 'Restore refused.')

vi.mock('@/i18n', () => ({
  default: {
    global: { t: key => (key === 'common.apiError.backup_key_mismatch' ? REFUSED : key) },
  },
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
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
