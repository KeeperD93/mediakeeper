/**
 * Covers useFocusTrap wired into MMRenameFolderModal: initial focus on
 * the close button, Escape routing through the close handler, and
 * keydown listener detachment on unmount.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/composables/useMediaManager', async () => {
  const { ref } = await import('vue')
  const modalRenameFolderShow = ref(false)
  const renameFolderCurrent = ref('OldName')
  const renameFolderValue = ref('OldName')
  const activeCat = ref('movies')
  const subPath = ref('')
  const execRenameFolder = vi.fn()
  const CATS = ref([{ key: 'movies', label: 'Movies', path: '' }])
  return {
    useMediaManager: () => ({
      modalRenameFolderShow,
      renameFolderCurrent,
      renameFolderValue,
      activeCat,
      subPath,
      execRenameFolder,
    }),
    CATS,
  }
})

vi.mock('lucide-vue-next', () => ({
  Check: { name: 'CheckStub', template: '<i />' },
  ChevronRight: { name: 'ChevronRightStub', template: '<i />' },
  Folder: { name: 'FolderStub', template: '<i />' },
  Pencil: { name: 'PencilStub', template: '<i />' },
  X: { name: 'XStub', template: '<i />' },
}))

import MMRenameFolderModal from '@/components/media-manager/MMRenameFolderModal.vue'
import { useMediaManager } from '@/composables/useMediaManager'

function buildModal() {
  return mount(MMRenameFolderModal, {
    attachTo: document.body,
    global: {
      mocks: { $t: key => key },
    },
  })
}

describe('MMRenameFolderModal — focus trap integration', () => {
  beforeEach(() => {
    const m = useMediaManager()
    m.modalRenameFolderShow.value = true
    m.renameFolderCurrent.value = 'OldName'
    m.renameFolderValue.value = 'OldName'
    m.execRenameFolder.mockReset?.()
  })

  it('moves initial focus onto the close button when the dialog opens', async () => {
    const w = buildModal()
    await flushPromises()

    const closeBtn = w.get('.mr-close').element
    expect(document.activeElement).toBe(closeBtn)

    w.unmount()
  })

  it('routes Escape to the close handler exactly once', async () => {
    const w = buildModal()
    await flushPromises()

    const m = useMediaManager()
    expect(m.modalRenameFolderShow.value).toBe(true)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(m.modalRenameFolderShow.value).toBe(false)

    w.unmount()
  })

  it('detaches the keydown listener on unmount', async () => {
    const w = buildModal()
    await flushPromises()

    w.unmount()
    await flushPromises()

    const m = useMediaManager()
    m.modalRenameFolderShow.value = true
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(m.modalRenameFolderShow.value).toBe(true)
  })
})
