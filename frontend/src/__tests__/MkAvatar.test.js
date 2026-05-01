import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MkAvatar from '@/components/common/MkAvatar.vue'

describe('MkAvatar', () => {
  it('renders the first letter of the name when no src is provided', () => {
    const w = mount(MkAvatar, { props: { name: 'Alice' } })
    expect(w.text()).toContain('A')
    expect(w.find('img').exists()).toBe(false)
  })

  it('renders an <img> when src is provided', () => {
    const w = mount(MkAvatar, {
      props: { name: 'Alice', src: 'https://example.com/a.jpg' },
    })
    expect(w.find('img').exists()).toBe(true)
    expect(w.find('img').attributes('src')).toBe('https://example.com/a.jpg')
  })

  it('falls back to the letter on image load error', async () => {
    const w = mount(MkAvatar, {
      props: { name: 'Bob', src: 'https://example.com/missing.jpg' },
    })
    await w.find('img').trigger('error')
    expect(w.find('img').exists()).toBe(false)
    expect(w.text()).toContain('B')
  })

  it('applies the size prop to width/height style', () => {
    const w = mount(MkAvatar, { props: { name: 'X', size: 48 } })
    const el = w.element
    expect(el.style.width).toBe('48px')
    expect(el.style.height).toBe('48px')
  })
})
