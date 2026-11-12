/**
 * Period tabs of the leaderboard page: what follows the active tab, and what stays on screen.
 */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import { buildEntries, buildStats, composableState, mountPage } from './portalLeaderboardHarness'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))

vi.mock('@/composables/portal/useActivityLeaderboard', async () => {
  const { composableState: state } = await import('./portalLeaderboardHarness')
  return { useActivityLeaderboard: () => state }
})

describe('PortalLeaderboard.vue, period tabs', () => {
  it('opens on the month and asks the server for it', async () => {
    composableState.fetchTop.mockClear()
    const wrapper = await mountPage({ entries: buildEntries(8), stats: buildStats() })
    await flushPromises()
    expect(composableState.fetchTop.mock.calls).toEqual([[100, { period: 'month' }]])
    expect(wrapper.find('h1').text()).toBe('portal.leaderboard.title.month')
    const selected = wrapper.findAll('[role="tab"][aria-selected="true"]')
    expect(selected.map(tab => tab.text())).toEqual(['portal.leaderboard.periods.month'])
  })

  it.each(['today', 'week', 'all'])(
    'moves the title, the note and the request to %s',
    async period => {
      composableState.fetchTop.mockClear()
      const wrapper = await mountPage({ entries: buildEntries(8), stats: buildStats() })
      await flushPromises()
      const tab = wrapper
        .findAll('[role="tab"]')
        .find(item => item.text() === `portal.leaderboard.periods.${period}`)
      await tab.trigger('click')
      await flushPromises()
      expect(composableState.fetchTop).toHaveBeenLastCalledWith(100, { period })
      expect(wrapper.find('h1').text()).toBe(`portal.leaderboard.title.${period}`)
      expect(wrapper.find('.pt-lb-note').text()).toBe(`portal.leaderboard.scoringNote.${period}`)
    },
  )

  it('says the period is empty in its own words, and keeps the tabs to leave it', async () => {
    const wrapper = await mountPage({ entries: [] })
    await flushPromises()
    await wrapper.findAll('[role="tab"]')[0].trigger('click')
    await flushPromises()
    expect(wrapper.find('.pt-lb-state').text()).toBe('portal.leaderboard.emptyState.today')
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(4)
  })

  it('keeps the tabs on screen while a period loads', async () => {
    const wrapper = await mountPage({ entries: buildEntries(8), stats: buildStats() })
    composableState.loading.value = true
    await flushPromises()
    expect(wrapper.find('.pt-lb-state').text()).toBe('common.loading')
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(4)
    expect(wrapper.find('.lb-hero-stub').exists()).toBe(false)
  })

  it('ties the panel to the active tab for a screen reader', async () => {
    const wrapper = await mountPage({ entries: buildEntries(8), stats: buildStats() })
    await flushPromises()
    const panel = wrapper.find('[role="tabpanel"]')
    const active = wrapper.find('[role="tab"][aria-selected="true"]')
    expect(active.attributes('aria-controls')).toBe(panel.attributes('id'))
    expect(panel.attributes('aria-labelledby')).toBe(active.attributes('id'))

    await wrapper.findAll('[role="tab"]')[1].trigger('click')
    const next = wrapper.find('[role="tab"][aria-selected="true"]')
    expect(panel.attributes('aria-labelledby')).toBe(next.attributes('id'))
  })

  it.each([
    ['today', 'fr', 'Classement du jour', "Aucun joueur classé aujourd'hui."],
    ['week', 'fr', 'Classement de la semaine', 'Aucun joueur classé cette semaine.'],
    ['month', 'fr', 'Classement du mois', 'Aucun joueur classé ce mois.'],
    ['all', 'fr', 'Classement de tous les temps', "Aucun joueur classé pour l'instant."],
    ['today', 'en', 'Daily leaderboard', 'No ranked players today.'],
    ['week', 'en', 'Weekly leaderboard', 'No ranked players this week.'],
    ['month', 'en', 'Monthly leaderboard', 'No ranked players this month.'],
    ['all', 'en', 'All-time leaderboard', 'No ranked players yet.'],
  ])('on %s in %s, reads "%s"', async (period, locale, title, empty) => {
    const { createI18n } = await vi.importActual('vue-i18n')
    const { t } = createI18n({ legacy: false, locale, messages: { fr, en } }).global
    const wrapper = await mountPage({ entries: [], $t: t })
    const index = ['today', 'week', 'month', 'all'].indexOf(period)
    await wrapper.findAll('[role="tab"]')[index].trigger('click')
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe(title)
    expect(wrapper.find('.pt-lb-state').text()).toBe(empty)
  })
})
