/**
 * Premium leaderboard page — rendering coverage.
 *
 * Stubs the composable so we drive the page deterministically with a
 * fixture array of entries. The page must:
 *   - render exactly 3 podium cards + (N - 3) "rest" rows for the
 *     gc-lb-row treatment.
 *   - surface the emptyState message when the API returns nothing.
 *   - NOT mount the legacy ``AchievementBadge`` grid (regression
 *     guard — that block belonged to the old design).
 *   - hand each row to router-link with the right user_id.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

function buildEntries(count, { offsetRank = 1 } = {}) {
  return Array.from({ length: count }, (_, i) => ({
    rank: offsetRank + i,
    user_id: 1000 + i,
    display_name: `User ${offsetRank + i}`,
    avatar_url: null,
    level: 10 + i,
    tier: 'gold',
    title_key: 'regular',
    month_xp: 1000 - i * 10,
    selected_title: null,
    title_tier: null,
    is_current_user: false,
    movement: 0,
  }))
}

const composableState = {
  entries: ref([]),
  loading: ref(false),
  fetchTop: vi.fn(() => Promise.resolve(composableState.entries.value)),
}

vi.mock('@/composables/portal/useMonthlyLeaderboard', () => ({
  useMonthlyLeaderboard: () => composableState,
}))

const RouterLinkStub = {
  props: ['to'],
  template: '<a :data-to="JSON.stringify(to)"><slot /></a>',
}

async function mountPage(entries) {
  composableState.entries.value = entries
  composableState.loading.value = false
  const PortalLeaderboard = (await import('@/views/portal/PortalLeaderboard.vue')).default
  return mount(PortalLeaderboard, {
    global: {
      stubs: {
        'router-link': RouterLinkStub,
        MkAvatar: { template: '<div class="mk-avatar-stub" />' },
      },
    },
  })
}

describe('PortalLeaderboard.vue', () => {
  it('renders 3 podium cards + (N-3) rest rows for a full payload', async () => {
    const wrapper = await mountPage(buildEntries(5))
    await flushPromises()
    expect(wrapper.findAll('.pt-lb-podium-card')).toHaveLength(3)
    expect(wrapper.findAll('.gc-lb-row')).toHaveLength(2)
  })

  it('handles the 100-entry top — 3 podium + 97 rest rows', async () => {
    const wrapper = await mountPage(buildEntries(100))
    await flushPromises()
    expect(wrapper.findAll('.pt-lb-podium-card')).toHaveLength(3)
    expect(wrapper.findAll('.gc-lb-row')).toHaveLength(97)
  })

  it('renders the empty-state message when the API returns nothing', async () => {
    const wrapper = await mountPage([])
    await flushPromises()
    expect(wrapper.text()).toContain('portal.leaderboard.emptyState')
    expect(wrapper.find('.pt-lb-podium-card').exists()).toBe(false)
    expect(wrapper.find('.gc-lb-row').exists()).toBe(false)
  })

  it('never mounts the legacy AchievementBadge grid (regression guard)', async () => {
    const wrapper = await mountPage(buildEntries(8))
    await flushPromises()
    // The old design rendered <AchievementBadge /> nodes; the new page
    // must drop them entirely.
    expect(wrapper.find('.achievement-badge').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('AchievementBadge')
    expect(wrapper.html()).not.toContain('myProgress')
  })

  it('points each rest row at /portal/u/:id', async () => {
    const wrapper = await mountPage(buildEntries(5))
    await flushPromises()
    const rows = wrapper.findAll('.gc-lb-row')
    // First rest row is rank 4 — user_id 1003 with the buildEntries offset.
    const first = rows[0]
    expect(first.attributes('data-to')).toContain('"name":"portal-user-profile"')
    expect(first.attributes('data-to')).toContain('"id":1003')
  })
})
