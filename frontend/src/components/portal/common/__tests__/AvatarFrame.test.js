/**
 * Avatar with the frame of a Master trophy: one set of effects per frame, scaled to the
 * avatar, and the rank card of the profile drawn as it was before the component.
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import MkAvatar from '@/components/common/MkAvatar.vue'
import AvatarFrame from '@/components/portal/common/AvatarFrame.vue'
import RankSidebarCard from '@/components/portal/profile/RankSidebarCard.vue'

const classesIn = el => [...el.children].map(child => `${child.tagName}.${child.className}`)

describe('AvatarFrame.vue', () => {
  it('draws the avatar with its tier ring, at the size asked, without a frame', () => {
    const wrapper = mount(AvatarFrame, { props: { name: 'Alice', size: 44, tier: 'gold' } })
    const avatar = wrapper.findComponent(MkAvatar)
    expect(avatar.props()).toMatchObject({ name: 'Alice', size: 44, tier: 'gold', src: null })
    expect(wrapper.classes()).toEqual(['pt-avf', 'pt-avf--own'])
    expect(wrapper.attributes('style')).toContain('--pt-avf-default: 44')
    expect(wrapper.find('.pt-avf-layer').exists()).toBe(false)
  })

  it('draws the effects of the frame behind the avatar, in their original order', () => {
    const wrapper = mount(AvatarFrame, { props: { name: 'Alice', effect: 'special' } })
    const layer = wrapper.find('.pt-avf-layer')
    expect(layer.classes()).toEqual(['pt-avf-layer', 'gc-avatar-fx--special'])
    expect(layer.attributes('aria-hidden')).toBe('true')
    expect(classesIn(layer.element)).toEqual([
      'DIV.gc-fx-holy-rays',
      'DIV.gc-fx-holy-glow',
      'DIV.gc-fx-holy-ring',
      'DIV.gc-fx-rune',
      'DIV.gc-fx-rune',
      'DIV.gc-fx-rune',
      'DIV.gc-fx-rune',
    ])
    expect(wrapper.element.lastElementChild.classList).toContain('mk-avatar')
  })

  it('puts the ranking stars and their halos in front of the avatar', () => {
    const wrapper = mount(AvatarFrame, { props: { name: 'Alice', effect: 'ranking' } })
    const layers = wrapper.findAll('.pt-avf-layer')
    expect(layers).toHaveLength(1)
    expect(layers[0].classes()).toContain('pt-avf-layer--top')
    expect(wrapper.element.lastElementChild).toBe(layers[0].element)
    expect(layers[0].findAll('.gc-fx-rhalo')).toHaveLength(5)
    expect(layers[0].findAll('.gc-fx-rstar')).toHaveLength(5)
  })

  it('draws nothing around for a frame it does not know', () => {
    const wrapper = mount(AvatarFrame, { props: { name: 'Alice', effect: 'sparkles' } })
    expect(wrapper.find('.pt-avf-layer').exists()).toBe(false)
    expect(wrapper.classes()).not.toContain('pt-avf--fx')
  })

  it('keeps room for the frame only when asked and when there is one', () => {
    const framed = mount(AvatarFrame, { props: { name: 'Alice', effect: 'meta', reserve: true } })
    const bare = mount(AvatarFrame, { props: { name: 'Alice', reserve: true } })
    expect(framed.classes()).toContain('pt-avf--reserve')
    expect(bare.classes()).not.toContain('pt-avf--reserve')
  })
})

describe('RankSidebarCard.vue with AvatarFrame', () => {
  const card = effect =>
    mount(RankSidebarCard, {
      props: { profileData: { display_name: 'Alice', avatar_url: null, avatar_effect: effect } },
    })

  it('keeps the tier ring around the 88 px avatar of the card', () => {
    const zone = card(null).find('.gc-avatar-zone')
    const avatar = zone.find('.gc-avatar-ring > .gc-avatar-inner > .gc-avatar-mk')
    expect(avatar.exists()).toBe(true)
    expect(avatar.attributes('style')).toContain('width: 88px')
    expect(zone.find('.pt-avf-layer').exists()).toBe(false)
  })

  it('draws the chosen frame around it, with the room it had', () => {
    const zone = card('community').find('.gc-avatar-zone')
    const frame = zone.find('.pt-avf')
    expect(frame.classes()).toEqual(['pt-avf', 'pt-avf--fx', 'pt-avf--reserve'])
    expect(frame.attributes('style')).toContain('--pt-avf-default: 88')
    expect(classesIn(zone.find('.gc-avatar-fx--community').element)).toEqual([
      'DIV.gc-fx-nebula',
      ...Array(8).fill('SPAN.gc-fx-star'),
    ])
    expect(frame.find('.gc-avatar-ring .gc-avatar-mk').exists()).toBe(true)
  })

  it('ignores a frame that is not unlockable', () => {
    expect(card('sparkles').find('.pt-avf-layer').exists()).toBe(false)
  })
})
