import { describe, it, expect, vi, beforeEach } from 'vitest'

// vi.mock is hoisted above the file, so the spies it references must be created
// with vi.hoisted. renameHistory only needs a plain { value } (undoRename reads
// and mutates .value directly; no reactivity required for the assertions).
const h = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  saveSpy: vi.fn(),
  loadFilesSpy: vi.fn(),
  confirmSpy: vi.fn(),
  renameHistory: { value: [] },
}))

vi.mock('@/composables/mediaManagerState', () => ({
  apiFetch: h.apiFetch,
  showToast: vi.fn(),
  _t: (k, p) => (p ? `${k}:${JSON.stringify(p)}` : k),
  renameHistory: h.renameHistory,
  _saveRenameHistory: h.saveSpy,
  setProgress: vi.fn(),
  endProgress: vi.fn(),
  // Other named exports the module destructures at import (unused by undoRename).
  activeCat: { value: '' },
  filtered: { value: [] },
  checked: { value: new Set() },
  newNames: { value: [] },
  dragSrc: { value: null },
  modalConfirm: { value: {} },
  expandedMode: { value: false },
  fileRenameStatus: { value: {} },
  renameErrors: { value: [] },
  showRenameErrorsModal: { value: false },
  selectedTmdb: { value: null },
}))
vi.mock('@/composables/mediaManagerNavigation', () => ({
  loadFiles: h.loadFilesSpy,
  applyRenameInPlace: vi.fn(),
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => h.confirmSpy }))

import { undoRename } from '@/composables/mediaManagerRename'

const ITEMS = [
  { oldName: 'a.mkv', newName: 'A.mkv', path: '/m/a.mkv', newPath: '/m/A.mkv' },
  { oldName: 'b.mkv', newName: 'B.mkv', path: '/m/b.mkv', newPath: '/m/B.mkv' },
]
const entry = items => ({ timestamp: 1, cat: 'films', tmdbTitle: 'X', items })
const fakeRes = body => ({ json: async () => body })

describe('undoRename — single-batch revert', () => {
  beforeEach(() => {
    h.renameHistory.value = []
    h.apiFetch.mockReset()
    h.saveSpy.mockReset()
    h.confirmSpy.mockReset().mockResolvedValue(true)
  })

  it('reverts every file in ONE batch request and drops the entry on full success', async () => {
    h.renameHistory.value = [entry(ITEMS)]
    h.apiFetch.mockResolvedValue(fakeRes([{ success: true }, { success: true }]))
    await undoRename(0)
    expect(h.apiFetch).toHaveBeenCalledTimes(1)
    const body = JSON.parse(h.apiFetch.mock.calls[0][1].body)
    expect(body.items).toHaveLength(2)
    expect(body.items[0]).toEqual({ old_path: '/m/A.mkv', new_name: 'a.mkv' })
    expect(h.renameHistory.value).toHaveLength(0)
  })

  it('keeps only the un-reverted items when the batch partially fails', async () => {
    h.renameHistory.value = [entry(ITEMS)]
    h.apiFetch.mockResolvedValue(fakeRes([{ success: true }, { error: 'destination_exists' }]))
    await undoRename(0)
    expect(h.renameHistory.value).toHaveLength(1)
    expect(h.renameHistory.value[0].items).toHaveLength(1)
    expect(h.renameHistory.value[0].items[0].oldName).toBe('b.mkv')
  })

  it('keeps the whole entry when the request fails (e.g. 429) so undo stays available', async () => {
    h.renameHistory.value = [entry(ITEMS)]
    h.apiFetch.mockRejectedValue(new Error('429'))
    await undoRename(0)
    expect(h.renameHistory.value).toHaveLength(1)
    expect(h.renameHistory.value[0].items).toHaveLength(2)
  })

  it('does nothing when the confirm dialog is cancelled', async () => {
    h.renameHistory.value = [entry(ITEMS)]
    h.confirmSpy.mockResolvedValue(false)
    await undoRename(0)
    expect(h.apiFetch).not.toHaveBeenCalled()
    expect(h.renameHistory.value).toHaveLength(1)
  })
})
