import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RankSidebarCard from '@/components/portal/profile/RankSidebarCard.vue'

const baseProps = {
  rankTier: 'bronze',
  titleKey: 'spectator',
  titleTierName: 'mythic',
  ranking: { position: 12, percentile: 30, movement: 0 },
  memberSince: 4,
  xpPercent: 50,
  nextLevelXp: 2000,
  trophies: [],
  iconMap: {},
}

function makeWrapper(profileData) {
  return mount(RankSidebarCard, {
    props: { ...baseProps, profileData },
    global: {
      stubs: {
        MkAvatar: {
          props: ['name', 'src', 'size'],
          template:
            '<div class="mk-avatar-stub" :data-src="src" :data-name="name" :data-size="size"></div>',
        },
      },
      mocks: { $t: key => key },
    },
  })
}

describe('RankSidebarCard avatar delegation', () => {
  it('renders the MkAvatar silhouette when no avatar_url is supplied', () => {
    const w = makeWrapper({ display_name: 'Alice', avatar_url: null, xp: 1000, level: 4 })
    const stub = w.find('.mk-avatar-stub')
    expect(stub.exists()).toBe(true)
    // src arrives as null on the stub — Vue strips boolean/null attrs at render
    expect(stub.attributes('data-src')).toBeUndefined()
    expect(stub.attributes('data-name')).toBe('Alice')
  })

  it('passes the avatar_url through to MkAvatar when present', () => {
    const w = makeWrapper({
      display_name: 'Bob',
      avatar_url: 'https://example.test/bob.png',
      xp: 1000,
      level: 4,
    })
    const stub = w.find('.mk-avatar-stub')
    expect(stub.attributes('data-src')).toBe('https://example.test/bob.png')
  })

  it('no longer renders the legacy first-letter fallback', () => {
    const w = makeWrapper({ display_name: 'Charlie', avatar_url: null, xp: 1000, level: 4 })
    const html = w.html()
    expect(html).not.toContain('gc-avatar-letter')
    expect(html).not.toContain('charAt')
  })
})
