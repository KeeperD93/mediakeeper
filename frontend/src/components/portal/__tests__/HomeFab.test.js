import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'

import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

const chat = vi.hoisted(() => ({}))
vi.mock('@/composables/portal/usePortalChat', () => ({ usePortalChat: () => chat }))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: { value: { chat_enabled: true } } }),
}))

import HomeFab from '@/components/portal/HomeFab.vue'

// Pass a locale to use the real translations (plural forms included).
function mountFab(locale) {
  const mocks = locale
    ? { $t: createI18n({ legacy: false, locale, messages: { en, fr } }).global.t }
    : {}
  return mount(HomeFab, {
    global: {
      mocks,
      stubs: {
        ChatPanel: true,
        EventCreateModal: true,
        'transition-group': { template: '<div><slot /></div>' },
      },
    },
  })
}

describe('HomeFab', () => {
  beforeEach(() => {
    chat.unreadCount = ref(0)
    chat.markRead = vi.fn()
  })

  it('does not render a Promotion sub-button when expanded', async () => {
    const w = mountFab()
    await w.find('.pt-fab-main').trigger('click')

    const titles = w.findAll('button').map(b => b.attributes('title') || '')
    expect(titles.some(t => t.includes('portal.promotion'))).toBe(false)
    expect(w.findAll('.pt-fab-btn--disabled')).toHaveLength(0)
  })

  it('gives the main toggle a translated accessible name', () => {
    const main = mountFab().find('.pt-fab-main')
    expect(main.attributes('aria-label')).toBe('portal.nav.quickActions')
  })

  it.each([
    ['en', 0, 'Quick actions'],
    ['en', 1, 'Quick actions, 1 unread message'],
    ['en', 3, 'Quick actions, 3 unread messages'],
    ['fr', 0, 'Actions rapides'],
    ['fr', 1, 'Actions rapides, 1 message non lu'],
    ['fr', 3, 'Actions rapides, 3 messages non lus'],
  ])('names the collapsed toggle with the unread count (%s, %i)', (locale, unread, name) => {
    chat.unreadCount = ref(unread)
    const main = mountFab(locale).find('.pt-fab-main')
    expect(main.attributes('aria-label')).toBe(name)
    expect(main.find('.pt-fab-badge').exists()).toBe(unread > 0)
  })

  it('drops the count from the name once open, with the badge', async () => {
    chat.unreadCount = ref(3)
    const w = mountFab('en')
    await w.find('.pt-fab-main').trigger('click')

    const main = w.find('.pt-fab-main')
    expect(main.attributes('aria-label')).toBe('Quick actions')
    expect(main.find('.pt-fab-badge').exists()).toBe(false)
  })

  it('reflects the open state in aria-expanded', async () => {
    const w = mountFab()
    // Re-query after each click: the global Teleport stub re-creates the button.
    const main = () => w.find('.pt-fab-main')
    expect(main().attributes('aria-expanded')).toBe('false')

    await main().trigger('click')
    expect(main().attributes('aria-expanded')).toBe('true')
    expect(w.findAll('.pt-fab-btn').length).toBeGreaterThan(0)

    await main().trigger('click')
    expect(main().attributes('aria-expanded')).toBe('false')
    expect(w.findAll('.pt-fab-btn')).toHaveLength(0)
  })

  it('points aria-controls at the sub-button container', () => {
    const w = mountFab()
    const controls = w.find('.pt-fab-main').attributes('aria-controls')
    expect(controls).toBeTruthy()
    expect(w.find('.pt-fab-sub').attributes('id')).toBe(controls)
  })
})
