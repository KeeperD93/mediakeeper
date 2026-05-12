import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MkToggle from '@/components/common/MkToggle.vue'

describe('MkToggle', () => {
  it('renders aria-checked="false" when modelValue is false', () => {
    const w = mount(MkToggle, { props: { modelValue: false } })
    expect(w.attributes('aria-checked')).toBe('false')
    expect(w.classes()).not.toContain('mk-toggle--on')
  })

  it('renders aria-checked="true" when modelValue is true', () => {
    const w = mount(MkToggle, { props: { modelValue: true } })
    expect(w.attributes('aria-checked')).toBe('true')
    expect(w.classes()).toContain('mk-toggle--on')
  })

  it('emits update:modelValue=true on click when off', async () => {
    const w = mount(MkToggle, { props: { modelValue: false } })
    await w.trigger('click')
    expect(w.emitted('update:modelValue')).toEqual([[true]])
  })

  it('emits update:modelValue=false on click when on', async () => {
    const w = mount(MkToggle, { props: { modelValue: true } })
    await w.trigger('click')
    expect(w.emitted('update:modelValue')).toEqual([[false]])
  })

  it('toggles on Space keydown', async () => {
    const w = mount(MkToggle, { props: { modelValue: false } })
    await w.trigger('keydown', { key: ' ', code: 'Space' })
    expect(w.emitted('update:modelValue')).toEqual([[true]])
  })

  it('toggles on Enter keydown', async () => {
    const w = mount(MkToggle, { props: { modelValue: false } })
    await w.trigger('keydown', { key: 'Enter', code: 'Enter' })
    expect(w.emitted('update:modelValue')).toEqual([[true]])
  })

  it('does not emit when disabled', async () => {
    const w = mount(MkToggle, { props: { modelValue: false, disabled: true } })
    await w.trigger('click')
    expect(w.emitted('update:modelValue')).toBeUndefined()
  })

  it('exposes disabled attribute when disabled', () => {
    const w = mount(MkToggle, { props: { modelValue: false, disabled: true } })
    expect(w.attributes('disabled')).toBeDefined()
  })

  it('forwards ariaLabel to aria-label attribute', () => {
    const w = mount(MkToggle, { props: { modelValue: false, ariaLabel: 'Toggle X' } })
    expect(w.attributes('aria-label')).toBe('Toggle X')
  })
})
