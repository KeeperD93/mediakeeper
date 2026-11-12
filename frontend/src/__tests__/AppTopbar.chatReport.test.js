/**
 * Admin bell: a reported chat message is labelled with the real texts, and the
 * label follows a language switch without waiting for the next poll.
 */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))
vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'home', meta: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ user: ref({ username: 'Alice' }), logout: vi.fn() }),
}))

const CHAT_REPORTS = {
  items: [
    {
      id: 1,
      message_id: 2,
      message_content: 'Hello from Bob',
      message_deleted: false,
      message_author_name: 'Bob',
      created_at: '2026-01-01T10:00:00Z',
    },
  ],
}

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet: vi.fn(async url => {
      if (url.startsWith('/api/portal/admin/requests/chat/reports')) return CHAT_REPORTS
      if (url.startsWith('/api/feedback/reports')) return { items: [] }
      if (url === '/api/alerts/seen') return { seen: [] }
      if (url === '/api/emby/alerts') return []
      return null
    }),
    apiPost: vi.fn().mockResolvedValue({}),
    apiDelete: vi.fn().mockResolvedValue({}),
  }),
}))

import AppTopbar from '@/components/layout/AppTopbar.vue'

async function openBell(locale) {
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  const wrapper = mount(AppTopbar, {
    global: {
      plugins: [i18n],
      stubs: { MkAvatar: true, DonationOverlay: true, FeedbackModal: true },
    },
  })
  await flushPromises()
  await wrapper.find('.tb-action-wrap .tb-action-btn').trigger('click')
  await nextTick()
  return { wrapper, i18n }
}

describe('AppTopbar reported chat message', () => {
  it.each([
    ['fr', 'CHAT Message signalé : Hello from Bob'],
    ['en', 'CHAT Reported message: Hello from Bob'],
  ])('reads in %s', async (locale, shown) => {
    const { wrapper } = await openBell(locale)
    expect(wrapper.find('.tb-notif-text').text()).toBe(shown)
    wrapper.unmount()
  })

  it('follows a language switch at once', async () => {
    const { wrapper, i18n } = await openBell('en')
    i18n.global.locale.value = 'fr'
    await nextTick()
    expect(wrapper.find('.tb-notif-text').text()).toBe('CHAT Message signalé : Hello from Bob')
    wrapper.unmount()
  })
})
