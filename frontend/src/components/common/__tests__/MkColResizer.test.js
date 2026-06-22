import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MkColResizer from '@/components/common/MkColResizer.vue'

describe('MkColResizer', () => {
  it('exposes a vertical separator role for assistive tech', () => {
    const w = mount(MkColResizer, { props: { index: 2 } })
    expect(w.attributes('role')).toBe('separator')
    expect(w.attributes('aria-orientation')).toBe('vertical')
  })

  it('emits start with its column index and the event on pointerdown', async () => {
    const w = mount(MkColResizer, { props: { index: 2 } })
    await w.trigger('pointerdown')
    const start = w.emitted('start')
    expect(start).toBeTruthy()
    expect(start).toHaveLength(1)
    expect(start[0][0]).toBe(2) // the column index
    expect(start[0][1]).toBeDefined() // the pointer event passed through
  })
})
