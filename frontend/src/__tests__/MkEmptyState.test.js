import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

describe('MkEmptyState', () => {
  it('renders the title and optional sub', () => {
    const w = mount(MkEmptyState, {
      props: { title: 'Nothing here', sub: 'Try again later' },
    })
    expect(w.text()).toContain('Nothing here')
    expect(w.text()).toContain('Try again later')
  })

  it('does not render the sub paragraph when sub is absent', () => {
    const w = mount(MkEmptyState, { props: { title: 'Empty' } })
    expect(w.find('.mk-empty-sub').exists()).toBe(false)
  })

  it('switches to the sm variant', () => {
    const w = mount(MkEmptyState, { props: { title: 'x', size: 'sm' } })
    expect(w.classes()).toContain('mk-empty-sm')
  })
})
