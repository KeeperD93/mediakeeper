import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import RankSidebarCard from '@/components/portal/profile/RankSidebarCard.vue'
import PortalUserProfile from '@/views/portal/PortalUserProfile.vue'

const apiGet = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '5' } }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet }) }))
vi.mock('@/composables/portal/usePortalAchievements', () => ({
  usePortalAchievements: () => ({ fetchUserAchievements: vi.fn().mockResolvedValue([]) }),
}))

const profile = {
  id: 5,
  user_id: 5,
  display_name: 'Alice',
  level: 4,
  xp: 1000,
  is_self: true,
  achievements: { unlocked: 0, total: 10, unlocked_ids: [] },
}

async function mountWith(payload) {
  apiGet.mockResolvedValue(payload)
  const wrapper = mount(PortalUserProfile, {
    global: {
      stubs: { RankSidebarCard: true, MkSpinner: true },
      mocks: { $t: (key, params) => (params ? `${key} ${JSON.stringify(params)}` : key) },
    },
  })
  await flushPromises()
  return wrapper
}

describe('PortalUserProfile.vue, ranking stat', () => {
  beforeEach(() => apiGet.mockReset())

  it('shows the percentile next to a place', async () => {
    const wrapper = await mountWith({ ...profile, ranking: { position: 3, percentile: 12 } })

    expect(wrapper.find('.pt-up-stats small').text()).toBe(
      '· portal.profile.topPercent {"percent":12}',
    )
  })

  it('shows no percentile without a place', async () => {
    const wrapper = await mountWith({ ...profile, ranking: { position: 0, percentile: 0 } })

    expect(wrapper.find('.pt-up-stats small').exists()).toBe(false)
  })
})

describe('PortalUserProfile.vue, level bar', () => {
  beforeEach(() => apiGet.mockReset())

  it('fills the level 1 bar from 0 XP', async () => {
    const wrapper = await mountWith({ ...profile, level: 1, xp: 50 })
    const card = wrapper.findComponent(RankSidebarCard)

    expect(card.props('nextLevelXp')).toBe(300)
    expect(card.props('xpPercent')).toBe(17)
  })

  it('rounds a half up, like the own profile and the daily digest', async () => {
    // 14.5 %: a float ratio reads 14.499… and rounded down to 14.
    const wrapper = await mountWith({ ...profile, level: 3, xp: 658 })

    expect(wrapper.findComponent(RankSidebarCard).props('xpPercent')).toBe(15)
  })
})

describe('PortalUserProfile.vue, private profile', () => {
  beforeEach(() => apiGet.mockReset())

  it('shows the illustration zone and the message instead of the profile', async () => {
    const wrapper = await mountWith({ is_private: true })

    expect(wrapper.find('.pt-up-private-art').exists()).toBe(true)
    expect(wrapper.find('h1').text()).toBe('portal.profile.privateProfile.title')
    expect(wrapper.find('.pt-up-private p').text()).toBe('portal.profile.privateProfile.desc')
    expect(wrapper.find('.pt-up-hero').exists()).toBe(false)
  })
})
