/**
 * Hero billboard — rendering coverage.
 *
 * The hero must mount the count-up XP value and reach the target after
 * the animation finishes. Stubs MkAvatar + router-link so the test
 * focuses on the billboard markup.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import LeaderboardHeroBillboard from '@/components/portal/leaderboard/LeaderboardHeroBillboard.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

const RouterLinkStub = {
  props: ['to'],
  template: '<a :data-to="JSON.stringify(to)"><slot /></a>',
}

function buildEntry(overrides = {}) {
  return {
    rank: 1,
    user_id: 7,
    display_name: 'Champion',
    avatar_url: null,
    level: 25,
    tier: 'gold',
    title_key: 'regular',
    month_xp: 2500,
    movement: 1,
    selected_title: null,
    title_tier: null,
    lead_over_2: 800,
    ...overrides,
  }
}

describe('LeaderboardHeroBillboard.vue', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => ({
        matches: false,
        addEventListener: () => {},
        removeEventListener: () => {},
      })),
    )
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('renders the rank, pseudo, level title and lead-over-2 chip', async () => {
    const wrapper = mount(LeaderboardHeroBillboard, {
      props: { entry: buildEntry() },
      global: {
        stubs: {
          'router-link': RouterLinkStub,
          MkAvatar: { template: '<div class="mk-avatar-stub" />' },
        },
      },
    })
    expect(wrapper.find('.lb-hero-rank-num').text()).toBe('#1')
    expect(wrapper.text()).toContain('Champion')
    // i18n is stubbed to return the key.
    expect(wrapper.text()).toContain('portal.leaderboard.hero.levelTitle')
    expect(wrapper.text()).toContain('portal.leaderboard.hero.leadOverSecond')
  })

  it('reaches the target XP at the end of the count-up animation', async () => {
    vi.useFakeTimers({
      toFake: ['performance', 'requestAnimationFrame', 'cancelAnimationFrame'],
    })
    const wrapper = mount(LeaderboardHeroBillboard, {
      props: { entry: buildEntry({ month_xp: 1500 }) },
      global: {
        stubs: {
          'router-link': RouterLinkStub,
          MkAvatar: { template: '<div class="mk-avatar-stub" />' },
        },
      },
    })
    // Default duration is 1400 ms — advance well past it.
    vi.advanceTimersByTime(1600)
    await wrapper.vm.$nextTick()
    const xpValue = wrapper
      .find('.lb-hero-xp-value')
      .text()
      .replace(/[^0-9]/g, '')
    expect(xpValue).toBe('1500')
  })
})
