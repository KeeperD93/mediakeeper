import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MkSpinner from '@/components/common/MkSpinner.vue'

describe('MkSpinner', () => {
  it('renders with default size (md) and inline=false', () => {
    const w = mount(MkSpinner)
    expect(w.classes()).toContain('mk-spinner')
    expect(w.classes()).toContain('mk-spinner-md')
    expect(w.classes()).not.toContain('mk-spinner-inline')
  })

  it('applies the size modifier for sm / lg', () => {
    const sm = mount(MkSpinner, { props: { size: 'sm' } })
    expect(sm.classes()).toContain('mk-spinner-sm')

    const lg = mount(MkSpinner, { props: { size: 'lg' } })
    expect(lg.classes()).toContain('mk-spinner-lg')
  })

  it('applies the inline modifier when inline=true', () => {
    const w = mount(MkSpinner, { props: { inline: true } })
    expect(w.classes()).toContain('mk-spinner-inline')
  })
})
