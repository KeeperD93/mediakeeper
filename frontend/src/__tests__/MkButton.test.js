import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MkButton from '@/components/common/MkButton.vue'

describe('MkButton — variantes', () => {
  it('renders default primary variant with label slot', () => {
    const wrapper = mount(MkButton, { slots: { default: 'Enregistrer' } })
    expect(wrapper.element.tagName).toBe('BUTTON')
    expect(wrapper.classes()).toContain('mk-btn')
    expect(wrapper.classes()).toContain('mk-btn--primary')
    expect(wrapper.classes()).toContain('mk-btn--md')
    expect(wrapper.text()).toBe('Enregistrer')
  })

  it.each([
    ['primary', 'mk-btn--primary'],
    ['danger', 'mk-btn--danger'],
    ['success', 'mk-btn--success'],
    ['ghost', 'mk-btn--ghost'],
    ['icon', 'mk-btn--icon'],
    ['link', 'mk-btn--link'],
  ])('applies the %s variant class', (variant, klass) => {
    const wrapper = mount(MkButton, { props: { variant } })
    expect(wrapper.classes()).toContain(klass)
  })

  it.each([
    ['sm', 'mk-btn--sm'],
    ['md', 'mk-btn--md'],
    ['lg', 'mk-btn--lg'],
  ])('applies the %s size class', (size, klass) => {
    const wrapper = mount(MkButton, { props: { size } })
    expect(wrapper.classes()).toContain(klass)
  })

  it('icon variant is icon-only even without explicit icon', () => {
    const wrapper = mount(MkButton, {
      props: { variant: 'icon', ariaLabel: 'Paramètres' },
    })
    expect(wrapper.classes()).toContain('mk-btn--icon-only')
    expect(wrapper.attributes('aria-label')).toBe('Paramètres')
  })

  it('non-icon variant without slot but with icon prop becomes icon-only', () => {
    const wrapper = mount(MkButton, { props: { variant: 'primary', icon: 'save' } })
    expect(wrapper.classes()).toContain('mk-btn--icon-only')
  })
})

describe('MkButton — états', () => {
  it('disabled prop applies the disabled attribute', () => {
    const wrapper = mount(MkButton, {
      props: { disabled: true },
      slots: { default: 'Enregistrer' },
    })
    expect(wrapper.attributes('disabled')).toBeDefined()
  })

  it('loading prop disables the button and sets aria-busy', () => {
    const wrapper = mount(MkButton, {
      props: { loading: true },
      slots: { default: 'Enregistrement…' },
    })
    expect(wrapper.attributes('disabled')).toBeDefined()
    expect(wrapper.attributes('aria-busy')).toBe('true')
    expect(wrapper.classes()).toContain('mk-btn--loading')
    expect(wrapper.find('.mk-btn-spinner').exists()).toBe(true)
  })

  it('fullwidth prop adds the fullwidth class', () => {
    const wrapper = mount(MkButton, { props: { fullwidth: true } })
    expect(wrapper.classes()).toContain('mk-btn--fullwidth')
  })

  it('aria-busy is absent when not loading', () => {
    const wrapper = mount(MkButton, { slots: { default: 'X' } })
    expect(wrapper.attributes('aria-busy')).toBeUndefined()
  })

  it('emits click event on user click', async () => {
    const wrapper = mount(MkButton, { slots: { default: 'X' } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })
})

describe('MkButton — icônes', () => {
  it('renders a left icon when icon prop matches whitelist', () => {
    const wrapper = mount(MkButton, {
      props: { icon: 'save' },
      slots: { default: 'Enregistrer' },
    })
    expect(wrapper.find('.mk-btn-icon').exists()).toBe(true)
  })

  it('renders nothing when icon prop is not in the whitelist', () => {
    const wrapper = mount(MkButton, {
      props: { icon: 'unknown-icon-xyz' },
      slots: { default: 'X' },
    })
    expect(wrapper.find('.mk-btn-icon').exists()).toBe(false)
  })

  it('renders an icon on the right when iconRight prop is set', () => {
    const wrapper = mount(MkButton, {
      props: { iconRight: 'chevron-right' },
      slots: { default: 'Suivant' },
    })
    const icons = wrapper.findAll('.mk-btn-icon')
    expect(icons).toHaveLength(1)
  })

  it('hides icons while loading, shows only the spinner', () => {
    const wrapper = mount(MkButton, {
      props: { icon: 'save', iconRight: 'chevron-right', loading: true },
      slots: { default: 'X' },
    })
    expect(wrapper.find('.mk-btn-spinner').exists()).toBe(true)
    expect(wrapper.findAll('.mk-btn-icon')).toHaveLength(0)
  })
})

describe('MkButton — validation', () => {
  it('defaults type to button (not submit)', () => {
    const wrapper = mount(MkButton)
    expect(wrapper.attributes('type')).toBe('button')
  })

  it('honours an explicit type prop', () => {
    const wrapper = mount(MkButton, { props: { type: 'submit' } })
    expect(wrapper.attributes('type')).toBe('submit')
  })
})
