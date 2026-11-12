/**
 * Daily digest: its top 3 of the month draws the rows of "My profile", the viewer's
 * label included, framed by its section rather than as the admin widget.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

import PortalDailyDigestOverlay from '@/components/portal/PortalDailyDigestOverlay.vue'
import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'

const apiGet = vi.fn()

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ locale: ref('fr'), t: key => key }),
}))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPost: vi.fn() }) }))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: ref({ display_name: 'Alice' }) }),
}))

const row = (rank, name, extra = {}) => ({
  rank,
  user_id: 1000 + rank,
  display_name: name,
  avatar_url: null,
  level: 10,
  tier: 'gold',
  title_key: 'spectator',
  period_xp: 100 - rank,
  movement: 0,
  trophies_won: 0,
  is_current_user: false,
  ...extra,
})

const DIGEST = {
  empty: false,
  ranking: {
    position: 42,
    total: 50,
    movement: 0,
    top3: [
      row(1, 'Bob'),
      row(2, 'Carol'),
      row(3, 'Dave'),
      row(42, 'Alice', { is_current_user: true }),
    ],
  },
  recent_adds: [],
  events: [],
}

let wrapper

async function openDigest() {
  apiGet.mockResolvedValue({ dismissed: false, digest: DIGEST })
  wrapper = mount(PortalDailyDigestOverlay)
  await flushPromises()
  return wrapper.find('.ddd-section--leaderboard')
}

describe('PortalDailyDigestOverlay.vue, top 3 of the month', () => {
  afterEach(() => wrapper?.unmount())

  it('draws the rows of My profile under the title of its section', async () => {
    const section = await openDigest()
    const card = wrapper.findComponent(LeaderboardCard)
    expect(card.props('digest')).toBe(true)
    expect(card.props('widget')).toBe(false)
    expect(card.classes()).not.toContain('gc-lb-box--widget')
    expect(section.find('h3').text()).toBe('portal.dailyDigest.sections.top3')
    expect(section.find('.gc-box-title').exists()).toBe(false)
  })

  it('labels the row of the viewer after the top 3, and no other', async () => {
    const rows = (await openDigest()).findAll('.gc-lb-row')
    expect(rows.map(item => item.find('.gc-lb-n').text())).toEqual([
      'Bob',
      'Carol',
      'Dave',
      'Alice',
    ])
    expect(rows.map(item => item.find('.lb-me-pill').exists())).toEqual([false, false, false, true])
    expect(rows[3].classes()).toContain('gc-lb-row--me')
  })
})
