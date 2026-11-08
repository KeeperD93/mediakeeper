import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

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
