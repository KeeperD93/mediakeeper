import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PremiumRibbon from '@/components/portal/PremiumRibbon.vue'

describe('PremiumRibbon — title attribute', () => {
  it('renders the native HTML title attribute when title is provided', () => {
    const w = mount(PremiumRibbon, {
      props: { label: 'NEW', bg: 'var(--portal-color-success)', title: 'Added on May 14, 2026' },
    })
    const ribbon = w.find('.mk-ribbon')
    expect(ribbon.exists()).toBe(true)
    expect(ribbon.attributes('title')).toBe('Added on May 14, 2026')
  })

  it('omits the title attribute when title is an empty string', () => {
    const w = mount(PremiumRibbon, {
      props: { label: 'NEW', bg: 'var(--portal-color-success)' },
    })
    const ribbon = w.find('.mk-ribbon')
    // null bindings leave the attribute off the DOM, which the browser
    // treats as "no tooltip" — important when the parent toggles tooltips.
    expect(ribbon.attributes('title')).toBeUndefined()
  })

  it('renders the count suffix when count > 1', () => {
    const w = mount(PremiumRibbon, {
      props: { label: 'REJECTED', bg: 'var(--portal-color-error)', count: 3 },
    })
    expect(w.text()).toContain('REJECTED ×3')
  })

  it('does not render the count suffix when count is 1 or below', () => {
    const w = mount(PremiumRibbon, {
      props: { label: 'NEW', bg: 'var(--portal-color-success)', count: 1 },
    })
    expect(w.text()).toBe('NEW')
  })

  it('adds the pulse modifier class when pulse is true', () => {
    const w = mount(PremiumRibbon, {
      props: { label: 'NEW', bg: 'var(--portal-color-success)', pulse: true },
    })
    expect(w.find('.mk-ribbon').classes()).toContain('mk-ribbon--pulse')
  })
})
