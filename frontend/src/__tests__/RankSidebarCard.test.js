import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RankSidebarCard from '@/components/portal/profile/RankSidebarCard.vue'
import SettingsHero from '@/components/portal/settings/SettingsHero.vue'

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

function makeWrapper(profileData, overrides = {}) {
  return mount(RankSidebarCard, {
    props: { ...baseProps, profileData, ...overrides },
    global: {
      stubs: {
        MkAvatar: {
          props: ['name', 'src', 'size'],
          template:
            '<div class="mk-avatar-stub" :data-src="src" :data-name="name" :data-size="size"></div>',
        },
      },
      mocks: { $t: (key, params) => (params ? `${key} ${JSON.stringify(params)}` : key) },
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

describe('RankSidebarCard ranking block', () => {
  const profile = { display_name: 'Alice', avatar_url: null, xp: 1000, level: 4 }

  it('shows the place, movement and percentile of a ranked player', () => {
    const w = makeWrapper(profile)
    expect(w.find('.gc-ranking-pos').text()).toBe('#12')
    expect(w.find('.gc-ranking-move').exists()).toBe(true)
    expect(w.find('.gc-ranking-pct-bar').exists()).toBe(true)
    expect(w.find('.gc-ranking-pct-text').text()).toBe('portal.profile.topPercent {"percent":30}')
  })

  it('shows neither movement nor percentile without a place', () => {
    const w = makeWrapper(profile, { ranking: { position: 0, percentile: 50, movement: 0 } })
    expect(w.find('.gc-ranking-pos').text()).toBe('#—')
    expect(w.find('.gc-ranking-move').exists()).toBe(false)
    expect(w.find('.gc-ranking-pct-bar').exists()).toBe(false)
    expect(w.find('.gc-ranking-pct-text').exists()).toBe(false)
  })
})

describe('RankSidebarCard level bar without a threshold', () => {
  const newcomer = { display_name: 'Alice', avatar_url: null, xp: 50, level: 1 }

  it('reads up to the level 2 threshold of a player starting at 0 XP', () => {
    const w = makeWrapper(newcomer, { nextLevelXp: undefined })
    expect(w.find('.gc-xp-text').text()).toBe('50 / 300 XP')
  })

  it('keeps that threshold inside the settings hero', () => {
    const w = mount(SettingsHero, {
      props: { profileData: newcomer },
      global: { stubs: { MkAvatar: true } },
    })
    expect(w.find('.gc-xp-text').text()).toBe('50 / 300 XP')
  })
})
