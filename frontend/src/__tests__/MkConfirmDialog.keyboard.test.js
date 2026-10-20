/**
 * Enter accepts the open confirmation only on a fresh press: a held key
 * repeats, and must not answer the prompt that shows after the first one.
 * A focused dialog button answers Enter itself: Cancel, focused when the
 * dialog opens, never confirms.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))

import MkConfirmDialog from '@/components/common/MkConfirmDialog.vue'
import { useConfirm, _useConfirmState } from '@/composables/useConfirm'

const confirm = useConfirm()
const { state, cancel } = _useConfirmState()

const pressEnter = repeat =>
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', repeat }))

describe('MkConfirmDialog — Enter', () => {
  afterEach(async () => {
    while (state.value.open) {
      cancel()
      await nextTick()
    }
  })

  it('ignores a held Enter and accepts on a fresh press', async () => {
    const w = mount(MkConfirmDialog)
    let answer = null
    confirm({ title: 'Delete?' }).then(v => {
      answer = v
    })
    await flushPromises() // the dialog listens for keys once shown

    pressEnter(true)
    await flushPromises()
    expect(answer).toBeNull()

    pressEnter(false)
    await flushPromises()
    expect(answer).toBe(true)
    w.unmount()
  })

  it('does not confirm when Enter is pressed on the focused Cancel', async () => {
    const w = mount(MkConfirmDialog, { attachTo: document.body })
    let answer = null
    confirm({ title: 'Delete?', variant: 'danger' }).then(v => {
      answer = v
    })
    await flushPromises()
    expect(document.activeElement).toBe(w.find('.mk-confirm-btn-cancel').element)

    document.activeElement.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    )
    await flushPromises()

    expect(answer).toBeNull()
    w.unmount()
  })
})
