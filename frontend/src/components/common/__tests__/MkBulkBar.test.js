import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MkBulkBar from '@/components/common/MkBulkBar.vue'

// Teleport is stubbed so the gated content renders inline and is queryable; the
// smoke test cares about the count>0 gate and the slots, not the body target.
const teleportStub = { global: { stubs: { teleport: true } } }

describe('MkBulkBar', () => {
  it('renders nothing when count is 0', () => {
    const w = mount(MkBulkBar, { props: { count: 0 }, ...teleportStub })
    expect(w.find('.bulk-bar').exists()).toBe(false)
  })

  it('renders the bar with both slots when count > 0', () => {
    const w = mount(MkBulkBar, {
      props: { count: 3 },
      slots: {
        count: '<span class="cnt">3 selected</span>',
        default: '<button class="act">Delete</button>',
      },
      ...teleportStub,
    })
    const bar = w.find('.bulk-bar')
    expect(bar.exists()).toBe(true)
    expect(bar.attributes('role')).toBe('region')
    expect(w.find('.cnt').text()).toBe('3 selected')
    expect(w.find('.act').exists()).toBe(true)
  })
})
