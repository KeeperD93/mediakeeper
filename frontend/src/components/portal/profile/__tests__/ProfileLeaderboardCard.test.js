/**
 * Ranking card of "My profile": the month is already there, the other periods are asked
 * for, and the shared card stays as it was on the admin widget and the daily digest.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import LeaderboardCard from '../LeaderboardCard.vue'
import ProfileLeaderboardCard from '../ProfileLeaderboardCard.vue'

const board = vi.hoisted(() => ({}))

vi.mock('@/composables/portal/useActivityLeaderboard', () => ({
  useActivityLeaderboard: () => board,
}))

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
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
  is_current_user: false,
  movement: 1,
  trophies_won: 0,
  ...extra,
})

const MONTH = [row(1, 'Alice'), row(2, 'Bob')]
const WEEK = [row(1, 'Carol'), row(2, 'Dave')]
const ME = row(42, 'Erin', { is_current_user: true })

function mountCard(monthEntries = MONTH) {
  return mount(ProfileLeaderboardCard, { props: { monthEntries } })
}

const names = wrapper => wrapper.findAll('.gc-lb-n').map(name => name.text())
const tabNamed = (wrapper, period) =>
  wrapper.findAll('[role="tab"]').find(tab => tab.attributes('id').endsWith(`-tab-${period}`))
const state = wrapper => wrapper.find('.gc-lb-state')

describe('ProfileLeaderboardCard.vue', () => {
  beforeEach(() => {
    board.entries = ref([])
    board.viewerEntry = ref(null)
    board.loading = ref(false)
    board.fetchTop = vi.fn(async () => {
      board.entries.value = WEEK
    })
  })

  it('opens on the month it was given, without asking the server', () => {
    const wrapper = mountCard()
    expect(names(wrapper)).toEqual(['Alice', 'Bob'])
    expect(board.fetchTop).not.toHaveBeenCalled()
    expect(wrapper.find('select').element.value).toBe('month')
    expect(tabNamed(wrapper, 'month').attributes('aria-selected')).toBe('true')
  })

  it.each(['today', 'week', 'all'])('asks for 15 rows of %s on its tab', async period => {
    const wrapper = mountCard()
    await tabNamed(wrapper, period).trigger('click')
    expect(board.fetchTop.mock.calls).toEqual([[15, { period }]])
    expect(names(wrapper)).toEqual(['Carol', 'Dave'])
  })

  it('does the same from the menu, and both controls agree', async () => {
    const wrapper = mountCard()
    await wrapper.find('select').setValue('week')
    expect(board.fetchTop.mock.calls).toEqual([[15, { period: 'week' }]])
    expect(tabNamed(wrapper, 'week').attributes('aria-selected')).toBe('true')
    await tabNamed(wrapper, 'all').trigger('click')
    expect(wrapper.find('select').element.value).toBe('all')
  })

  it('adds a viewer outside the top at the end of the list', async () => {
    board.viewerEntry.value = ME
    const wrapper = mountCard()
    await tabNamed(wrapper, 'week').trigger('click')
    expect(names(wrapper)).toEqual(['Carol', 'Dave', 'Erin'])
    expect(wrapper.findAll('.gc-lb-row').at(-1).classes()).toContain('gc-lb-row--me')
  })

  it('labels the row of the viewer, and no other', () => {
    const wrapper = mountCard([row(1, 'Alice'), row(2, 'Bob', { is_current_user: true })])
    const rows = wrapper.findAll('.gc-lb-row')
    expect(rows[0].find('.lb-me-pill').exists()).toBe(false)
    expect(rows[1].find('.lb-me-pill').exists()).toBe(true)
    expect(rows[1].find('.gc-lb-n').text()).toBe('Bob')
  })

  it('leaves the rows of the month alone, viewer included', () => {
    board.viewerEntry.value = ME
    expect(names(mountCard())).toEqual(['Alice', 'Bob'])
  })

  it('comes back to the month without a new request', async () => {
    const wrapper = mountCard()
    await tabNamed(wrapper, 'week').trigger('click')
    board.fetchTop.mockClear()
    await tabNamed(wrapper, 'month').trigger('click')
    expect(board.fetchTop).not.toHaveBeenCalled()
    expect(names(wrapper)).toEqual(['Alice', 'Bob'])
  })

  it('replaces the rows while a period loads, and keeps the controls', async () => {
    const wrapper = mountCard()
    await tabNamed(wrapper, 'week').trigger('click')
    board.loading.value = true
    await wrapper.vm.$nextTick()
    expect(state(wrapper).text()).toBe('common.loading')
    expect(names(wrapper)).toEqual([])
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(4)
    expect(wrapper.find('select').exists()).toBe(true)
  })

  it('is not held up on the month by a period left behind', async () => {
    const wrapper = mountCard()
    await tabNamed(wrapper, 'week').trigger('click')
    board.loading.value = true
    await tabNamed(wrapper, 'month').trigger('click')
    expect(state(wrapper).exists()).toBe(false)
    expect(names(wrapper)).toEqual(['Alice', 'Bob'])
  })

  it.each([
    ['month', 'portal.leaderboard.emptyState.month'],
    ['today', 'portal.leaderboard.emptyState.today'],
  ])('stays on screen when %s is empty, to leave it', async (period, text) => {
    board.fetchTop = vi.fn(async () => {})
    const wrapper = mountCard([])
    await wrapper.find('select').setValue(period)
    expect(state(wrapper).text()).toBe(text)
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(4)
  })

  it('ties the rows to the active tab for a screen reader', async () => {
    const wrapper = mountCard()
    const panel = wrapper.find('[role="tabpanel"]')
    const active = () => wrapper.find('[role="tab"][aria-selected="true"]')
    expect(active().attributes('aria-controls')).toBe(panel.attributes('id'))
    expect(panel.attributes('aria-labelledby')).toBe(active().attributes('id'))
    await tabNamed(wrapper, 'week').trigger('click')
    expect(panel.attributes('aria-labelledby')).toBe(active().attributes('id'))
  })

  it('names the menu and the card with the short title', () => {
    const wrapper = mountCard()
    const select = wrapper.find('select')
    expect(select.attributes('aria-label')).toBe('portal.leaderboard.periodsLabel')
    expect(select.classes()).toContain('mk-select-chevron')
    expect(select.findAll('option').map(option => option.text())).toEqual([
      'portal.leaderboard.periods.today',
      'portal.leaderboard.periods.week',
      'portal.leaderboard.periods.month',
      'portal.leaderboard.periods.all',
    ])
    expect(wrapper.find('.gc-box-title').text()).toBe('portal.profile.rankingShort')
  })

  it('names what the arrows compare with, on the period shown', async () => {
    const wrapper = mountCard()
    expect(wrapper.find('.gc-lb-move').attributes('title')).toBe('portal.leaderboard.move.month.up')
    await tabNamed(wrapper, 'week').trigger('click')
    expect(wrapper.find('.gc-lb-move').attributes('title')).toBe('portal.leaderboard.move.week.up')
  })

  it('shows no arrow where the period has no previous one', async () => {
    board.fetchTop = vi.fn(async () => {
      board.entries.value = [row(1, 'Carol', { movement: null })]
    })
    const wrapper = mountCard()
    await tabNamed(wrapper, 'all').trigger('click')
    expect(names(wrapper)).toEqual(['Carol'])
    expect(wrapper.find('.gc-lb-move').exists()).toBe(false)
  })
})

describe('LeaderboardCard.vue without a period', () => {
  const widget = (entries = MONTH) => mount(LeaderboardCard, { props: { entries, widget: true } })

  it('keeps the admin widget and the daily digest as they were', () => {
    const wrapper = widget()
    expect(wrapper.find('select').exists()).toBe(false)
    expect(wrapper.find('[role="tablist"]').exists()).toBe(false)
    expect(wrapper.find('[role="tabpanel"]').exists()).toBe(false)
    expect(wrapper.find('.gc-lb-rows').attributes('id')).toBeUndefined()
    expect(wrapper.classes()).toEqual(['gc-lb-box', 'gc-lb-box--widget'])
    expect(wrapper.find('.gc-box-title').text()).toBe('portal.profile.ranking')
  })

  it('does not add the label of the leaderboard page', () => {
    const wrapper = widget([row(1, 'Alice', { is_current_user: true })])
    expect(wrapper.find('.gc-lb-row--me').exists()).toBe(true)
    expect(wrapper.find('.lb-me-pill').exists()).toBe(false)
  })

  it('reads the arrows against the last month', () => {
    expect(widget().find('.gc-lb-move').attributes('title')).toBe(
      'portal.leaderboard.move.month.up',
    )
  })

  it('shows neither a message nor a loading text when it has no rows', () => {
    const wrapper = mount(LeaderboardCard, {
      props: { entries: [], widget: true, loading: true },
    })
    expect(wrapper.find('.gc-lb-state').exists()).toBe(false)
  })

  it('stays away from the page when it has no rows and is no widget', () => {
    expect(
      mount(LeaderboardCard, { props: { entries: [] } })
        .find('.gc-lb-box')
        .exists(),
    ).toBe(false)
  })

  it('reserves the room of a full list only past the top and the viewer', () => {
    const rows = count => Array.from({ length: count }, (_, i) => row(i + 1, `Player ${i}`))
    const full = count =>
      mount(LeaderboardCard, { props: { entries: rows(count) } })
        .find('.gc-lb-rows')
        .attributes('data-full')
    expect(full(15)).toBeUndefined()
    expect(full(16)).toBe('true')
  })
})
