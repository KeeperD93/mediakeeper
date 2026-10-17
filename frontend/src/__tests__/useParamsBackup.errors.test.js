/**
 * Backup settings errors: a retention value outside the screen's range is
 * explained before anything is sent, a failed action gives the server's
 * reason or else says which action failed (never a blanket network error),
 * and a backup written without some parts names them.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BACKUP_RETENTION_MODE } from '@/constants/backup'
import { TOAST_TYPE } from '@/constants/toast'

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), apiGet: vi.fn(), showToast: vi.fn() }))
// Fake translations behind resolveApiError: an unknown key comes back
// unchanged, as with vue-i18n. The screen's own keys are echoed as-is.
const MESSAGES = vi.hoisted(() => ({
  'common.apiError.backup_not_found': 'Backup not found.',
  'common.apiError.backup_create_failed': 'Could not create the backup.',
  'common.apiError.backup_directory_invalid': 'Invalid backup directory.',
  'common.apiError.file_must_be_zip': 'The file must be a .zip archive.',
}))
const t = (key, named) => key + (named ? JSON.stringify(named) : '')

vi.mock('@/i18n', () => ({
  default: {
    global: { t: (key, named) => MESSAGES[key]?.replace('{status}', named?.status) ?? key },
  },
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t }) }))
vi.mock('@/composables/useApi', async importOriginal => ({
  ...(await importOriginal()),
  useApi: () => ({ apiFetch: mocks.apiFetch, apiGet: mocks.apiGet }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mocks.showToast }) }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => async () => true }))

import { useParamsBackup } from '@/composables/useParamsBackup'

const sentDays = () => JSON.parse(mocks.apiFetch.mock.calls.at(-1)[1].body).days
const lastToast = () => mocks.showToast.mock.calls.at(-1)

describe('useParamsBackup — retention', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.apiFetch.mockResolvedValue({ json: async () => ({ success: true }) })
  })

  it('explains a period outside 1 to 365 days instead of sending it', async () => {
    const b = useParamsBackup()
    b.retentionMode.value = BACKUP_RETENTION_MODE.DAYS

    for (const value of [500, -5, 2.5]) {
      b.retentionDays.value = value
      await b.saveRetention()
      expect(lastToast()).toEqual(['backup.retentionDaysRange{"max":365}', TOAST_TYPE.ERR])
    }
    expect(mocks.apiFetch).not.toHaveBeenCalled()
  })

  it('explains a backup count outside 1 to 100', async () => {
    const b = useParamsBackup()
    b.retentionMode.value = BACKUP_RETENTION_MODE.COUNT
    b.retentionCount.value = 101

    await b.saveRetention()

    expect(lastToast()).toEqual(['backup.retentionCountRange{"max":100}', TOAST_TYPE.ERR])
    expect(mocks.apiFetch).not.toHaveBeenCalled()
  })

  it('sends days, a negative count, or 0 when off', async () => {
    const b = useParamsBackup()

    b.retentionMode.value = BACKUP_RETENTION_MODE.DAYS
    b.retentionDays.value = 365
    await b.saveRetention()
    expect(sentDays()).toBe(365)

    b.retentionMode.value = BACKUP_RETENTION_MODE.COUNT
    b.retentionCount.value = 5
    await b.saveRetention()
    expect(sentDays()).toBe(-5)

    b.retentionMode.value = BACKUP_RETENTION_MODE.OFF
    await b.saveRetention()
    expect(sentDays()).toBe(0)
    expect(lastToast()).toEqual(['backup.retentionSaved', TOAST_TYPE.OK])
  })
})

describe('useParamsBackup — creating a backup', () => {
  beforeEach(() => vi.clearAllMocks())

  it('includes the database by default, like the scheduled backup', () => {
    expect(useParamsBackup().selectedComponents.value.pg_dump).toBe(true)
  })

  it('lists the optional log files last', () => {
    expect(Object.keys(useParamsBackup().selectedComponents.value).at(-1)).toBe('logs')
  })

  it('warns about a backup written without some parts, naming them', async () => {
    mocks.apiFetch.mockResolvedValue({
      json: async () => ({ success: true, failed_components: ['pg_dump'] }),
    })

    await useParamsBackup().createBackup()

    expect(mocks.showToast).toHaveBeenCalledWith(
      'backup.createdIncomplete{"parts":"backup.compPgDump"}',
      TOAST_TYPE.WARN,
    )
  })

  it('confirms a complete backup', async () => {
    mocks.apiFetch.mockResolvedValue({
      json: async () => ({ success: true, failed_components: [] }),
    })

    await useParamsBackup().createBackup()

    expect(mocks.showToast).toHaveBeenCalledWith('backup.created', TOAST_TYPE.OK)
  })
})

describe('useParamsBackup — failed actions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it("names the server's reason", async () => {
    mocks.apiFetch.mockRejectedValue(new Error('backup_not_found'))

    await useParamsBackup().deleteBackup('mediakeeper_backup_x.zip')

    expect(lastToast()).toEqual(['Backup not found.', TOAST_TYPE.ERR])
  })

  it('says which action failed when the server gives no reason', async () => {
    for (const failure of [new Error('http_502'), new TypeError('Failed to fetch')]) {
      mocks.apiFetch.mockRejectedValueOnce(failure)
      await useParamsBackup().createBackup()
      expect(lastToast()).toEqual(['Could not create the backup.', TOAST_TYPE.ERR])
    }
  })

  it('says the retention policy was not saved, not a network error', async () => {
    mocks.apiFetch.mockRejectedValue(new Error('http_500'))
    const b = useParamsBackup()
    b.retentionMode.value = BACKUP_RETENTION_MODE.DAYS
    b.retentionDays.value = 30

    await b.saveRetention()

    expect(lastToast()).toEqual(['backup.retentionSaveFailed', TOAST_TYPE.ERR])
  })

  it('says the backups could not be loaded', async () => {
    mocks.apiGet.mockRejectedValue(new Error('http_500'))
    const b = useParamsBackup()

    await b.loadBackupInfo()

    expect(lastToast()).toEqual(['common.apiError.loadFailed', TOAST_TYPE.ERR])
    expect(b.backupLoading.value).toBe(false)
  })

  it('logs a failed folder list without a toast', async () => {
    mocks.apiGet.mockRejectedValue(new Error('http_500'))

    await useParamsBackup().loadBackupDirs()

    expect(console.error).toHaveBeenCalledWith(
      '[useParamsBackup.loadBackupDirs]',
      expect.any(Error),
    )
    expect(mocks.showToast).not.toHaveBeenCalled()
  })

  it('explains a directory locked by the configuration, names other reasons', async () => {
    const b = useParamsBackup()
    const cases = [
      ['backup_directory_locked', 'backup.dirLocked'],
      ['backup_directory_invalid', 'Invalid backup directory.'],
      ['http_500', 'backup.dirChangeFailed'],
    ]
    for (const [code, message] of cases) {
      mocks.apiFetch.mockRejectedValueOnce(new Error(code))
      await b.changeBackupDir('/data/elsewhere')
      expect(lastToast()).toEqual([message, TOAST_TYPE.ERR])
    }
  })

  it('says a restore failed when the server gives no reason', async () => {
    mocks.apiFetch.mockRejectedValue(new Error('http_500'))
    const b = useParamsBackup()

    await b.restoreBackup('mediakeeper_backup_x.zip')

    expect(lastToast()).toEqual(['common.apiError.backup_restore_failed', TOAST_TYPE.ERR])
    expect(b.backupRestoring.value).toBeNull()
  })

  it("names the server's reason for a refused upload and clears the file input", async () => {
    mocks.apiFetch.mockRejectedValue(new Error('file_must_be_zip'))
    const event = { target: { files: [new File(['x'], 'backup.tar')], value: 'backup.tar' } }

    await useParamsBackup().uploadRestore(event)

    expect(lastToast()).toEqual(['The file must be a .zip archive.', TOAST_TYPE.ERR])
    expect(event.target.value).toBe('')
  })
})
