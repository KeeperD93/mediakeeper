/**
 * Media manager failures read as messages, never as raw codes: a move toast
 * per failed file (none for a rate limit, whose own toast says it), and a
 * reason for every file in the rename error list.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const h = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  showToast: vi.fn(),
  renameErrors: { value: [] },
  newNames: { value: [] },
}))

vi.mock('@/composables/mediaManagerState', () => ({
  apiGet: vi.fn(),
  apiFetch: h.apiFetch,
  showToast: h.showToast,
  _t: (k, p) => (p ? `${k}:${JSON.stringify(p)}` : k),
  activeCat: { value: 'films' },
  filtered: { value: [] },
  checked: { value: new Set() },
  dragFileIdx: { value: null },
  dragIsGrouped: { value: false },
  dragOverCat: { value: null },
  moveConflicts: { value: [] },
  showMoveConflictModal: { value: false },
  pendingMoveFiles: { value: [] },
  pendingMoveDest: { value: '' },
  moveHistory: { value: [] },
  _saveMoveHistory: vi.fn(),
  newNames: h.newNames,
  dragSrc: { value: null },
  modalConfirm: { value: {} },
  expandedMode: { value: false },
  renameHistory: { value: [] },
  _saveRenameHistory: vi.fn(),
  fileRenameStatus: { value: {} },
  renameErrors: h.renameErrors,
  showRenameErrorsModal: { value: false },
  selectedTmdb: { value: null },
  setProgress: vi.fn(),
  endProgress: vi.fn(),
}))
vi.mock('@/composables/mediaManagerNavigation', () => ({
  loadFiles: vi.fn(),
  applyRenameInPlace: vi.fn(),
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => vi.fn() }))
// A rate limit resolves to nothing; any other code to its message.
vi.mock('@/composables/useApi', () => ({
  resolveApiError: code => (code === 'rate_limited_notified' ? '' : `message:${code}`),
}))

import { _execMoveFiles } from '@/composables/mediaManagerMove'
import { execRename } from '@/composables/mediaManagerRename'

const ok = { json: async () => ({ success: true }) }
const file = name => ({ name, path: `/media/${name}` })
const toasts = type => h.showToast.mock.calls.filter(([, t]) => t === type).map(([m]) => m)

describe('media manager — failures', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    h.renameErrors.value = []
  })

  it('a move shows one toast per failed file, none for a rate limit', async () => {
    h.apiFetch
      .mockResolvedValueOnce(ok)
      .mockRejectedValueOnce(new Error('rate_limited_notified'))
      .mockRejectedValueOnce(new Error('http_500'))

    await _execMoveFiles([file('a.mkv'), file('b.mkv'), file('c.mkv')], '/media/dest', false)

    expect(toasts('err')).toEqual(['c.mkv : message:http_500'])
    expect(toasts('warn')).toEqual(['mediaManager.partialResult:{"ok":1,"errors":2}'])
  })

  it('a rename lists every failed file with a reason, the rate limit included', async () => {
    h.newNames.value = [
      { path: '/media/a.mkv', oldName: 'a.mkv', name: 'A.mkv' },
      { path: '/media/b.mkv', oldName: 'b.mkv', name: 'B.mkv' },
    ]
    h.apiFetch
      .mockRejectedValueOnce(new Error('rate_limited_notified'))
      .mockRejectedValueOnce(new Error('http_500'))

    await execRename()

    expect(h.renameErrors.value.map(e => e.reason)).toEqual([
      'common.apiError.rate_limited',
      'message:http_500',
    ])
  })
})
