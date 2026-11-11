/**
 * Period tabs — the order of the periods, what a screen reader is told and the keyboard.
 */
import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import LeaderboardPeriodTabs from '../LeaderboardPeriodTabs.vue'

let wrapper

function mountTabs(modelValue = 'month') {
  wrapper = mount(LeaderboardPeriodTabs, {
    attachTo: document.body,
    props: {
      baseId: 'board',
      modelValue,
      'onUpdate:modelValue': value => wrapper.setProps({ modelValue: value }),
    },
  })
  return wrapper
}

const tabs = () => wrapper.findAll('[role="tab"]')
const selected = () => tabs().filter(tab => tab.attributes('aria-selected') === 'true')

describe('LeaderboardPeriodTabs.vue', () => {
  afterEach(() => {
    wrapper.unmount()
  })

  it('lists today, week, month and all time, in this order', () => {
    mountTabs()
    expect(tabs().map(tab => tab.text())).toEqual([
      'portal.leaderboard.periods.today',
      'portal.leaderboard.periods.week',
      'portal.leaderboard.periods.month',
      'portal.leaderboard.periods.all',
    ])
  })

  it('names the tabs and the panel they control', () => {
    mountTabs()
    expect(wrapper.attributes('role')).toBe('tablist')
    expect(wrapper.attributes('aria-label')).toBe('portal.leaderboard.periodsLabel')
    expect(tabs()[2].attributes('id')).toBe('board-tab-month')
    expect(tabs()[2].attributes('aria-controls')).toBe('board-panel')
  })

  it('marks only the active tab, which alone takes the focus by Tab', () => {
    mountTabs('week')
    expect(selected().map(tab => tab.attributes('id'))).toEqual(['board-tab-week'])
    expect(tabs().map(tab => tab.attributes('tabindex'))).toEqual(['-1', '0', '-1', '-1'])
    expect(tabs()[1].classes()).toContain('lb-period-tab--on')
    expect(tabs()[2].classes()).not.toContain('lb-period-tab--on')
  })

  it('changes period on a click', async () => {
    mountTabs()
    await tabs()[3].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([['all']])
    expect(selected().map(tab => tab.attributes('id'))).toEqual(['board-tab-all'])
  })

  it.each([
    ['ArrowRight', 'month', 'all'],
    ['ArrowLeft', 'month', 'week'],
    // Both ends loop.
    ['ArrowRight', 'all', 'today'],
    ['ArrowLeft', 'today', 'all'],
    ['Home', 'all', 'today'],
    ['End', 'today', 'all'],
  ])('%s from %s goes to %s and follows with the focus', async (key, from, to) => {
    mountTabs(from)
    await tabs()
      .find(tab => tab.attributes('id') === `board-tab-${from}`)
      .trigger('keydown', { key })
    expect(wrapper.emitted('update:modelValue')).toEqual([[to]])
    expect(document.activeElement.id).toBe(`board-tab-${to}`)
  })

  it('takes the arrows away from the page, so it does not scroll sideways', () => {
    mountTabs()
    const event = new KeyboardEvent('keydown', {
      key: 'ArrowRight',
      bubbles: true,
      cancelable: true,
    })
    tabs()[2].element.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })

  it.each([
    ['another key', { key: 'a' }],
    ['the browser "back" shortcut', { key: 'ArrowLeft', altKey: true }],
    ['a shortcut with Ctrl', { key: 'ArrowRight', ctrlKey: true }],
    ['a shortcut with Cmd', { key: 'ArrowRight', metaKey: true }],
  ])('leaves %s to the browser', async (_, init) => {
    mountTabs()
    const event = new KeyboardEvent('keydown', { ...init, bubbles: true, cancelable: true })
    tabs()[2].element.dispatchEvent(event)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(event.defaultPrevented).toBe(false)
  })

  it.each([
    ['fr', ["Aujourd'hui", 'Semaine', 'Mois', 'Tout temps']],
    ['en', ['Today', 'Week', 'Month', 'All time']],
  ])('reads the validated labels in %s', (locale, labels) => {
    const { t } = createI18n({ legacy: false, locale, messages: { fr, en } }).global
    wrapper = mount(LeaderboardPeriodTabs, {
      props: { baseId: 'board', modelValue: 'month' },
      global: { mocks: { $t: t } },
    })
    expect(tabs().map(tab => tab.text())).toEqual(labels)
  })
})
