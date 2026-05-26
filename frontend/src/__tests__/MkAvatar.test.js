import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { UserRound } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'

describe('MkAvatar', () => {
  it('renders the UserRound silhouette when no src is provided', () => {
    const w = mount(MkAvatar, { props: { name: 'Alice' } })
    expect(w.findComponent(UserRound).exists()).toBe(true)
    expect(w.find('img').exists()).toBe(false)
  })

  it('renders an <img> when src is provided', () => {
    const w = mount(MkAvatar, {
      props: { name: 'Alice', src: 'https://example.com/a.jpg' },
    })
    expect(w.find('img').exists()).toBe(true)
    expect(w.find('img').attributes('src')).toBe('https://example.com/a.jpg')
    expect(w.findComponent(UserRound).exists()).toBe(false)
  })

  it('falls back to the silhouette on image load error', async () => {
    const w = mount(MkAvatar, {
      props: { name: 'Bob', src: 'https://example.com/missing.jpg' },
    })
    await w.find('img').trigger('error')
    expect(w.find('img').exists()).toBe(false)
    expect(w.findComponent(UserRound).exists()).toBe(true)
  })

  it('applies the size prop to width/height style', () => {
    const w = mount(MkAvatar, { props: { name: 'X', size: 48 } })
    const el = w.element
    expect(el.style.width).toBe('48px')
    expect(el.style.height).toBe('48px')
  })

  it('exposes the name as aria-label for screen readers', () => {
    const w = mount(MkAvatar, { props: { name: 'Charlie' } })
    expect(w.element.getAttribute('aria-label')).toBe('Charlie')
  })

  it('applies the tier ring class when the tier prop is set', () => {
    const w = mount(MkAvatar, { props: { name: 'X', tier: 'gold' } })
    expect(w.classes()).toContain('mk-avatar-tier--gold')
  })

  it('omits the tier ring class when no tier prop is passed', () => {
    const w = mount(MkAvatar, { props: { name: 'X' } })
    expect(w.classes().some(c => c.startsWith('mk-avatar-tier--'))).toBe(false)
  })

  it('accepts every documented tier value', () => {
    const tiers = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'master', 'legendary']
    for (const t of tiers) {
      const w = mount(MkAvatar, { props: { name: 'X', tier: t } })
      expect(w.classes()).toContain('mk-avatar-tier--' + t)
    }
  })
})
