/**
 * Movie night sheet: the capacity line, read with the real texts, because a plural call
 * given its values in the wrong place leaves the numbers empty without any error.
 */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

const getOne = vi.fn()
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ resolve: vi.fn() }) }))
vi.mock('@/composables/portal/useRooms', () => ({
  useRooms: () => ({ getOne, respond: vi.fn(), cancel: vi.fn(), removeMember: vi.fn() }),
}))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: ref({ user_id: 12345 }) }),
}))
vi.mock('@/composables/portal/useNotifications', () => ({
  useNotifications: () => ({ fetchCount: vi.fn() }),
}))

import EventDetailModal from '@/components/portal/EventDetailModal.vue'

async function capacityLine(locale, accepted) {
  getOne.mockResolvedValue({
    id: 1,
    kind: 'movie',
    title: 'Test Movie',
    status: 'scheduled',
    scheduled_at: '2026-06-15T20:00:00Z',
    max_participants: 8,
    accepted_count: accepted,
    is_full: false,
    tmdb_ids: [],
    invitations: [],
    creator_user_id: 12345,
  })
  const i18n = createI18n({ legacy: false, locale, messages: { fr, en } })
  const wrapper = mount(EventDetailModal, {
    props: { eventId: 1 },
    global: { plugins: [i18n] },
  })
  await flushPromises()
  const text = wrapper.findAll('.pt-evd-meta-item').at(-1).text()
  wrapper.unmount()
  return text
}

describe('EventDetailModal capacity', () => {
  it.each([
    ['fr', 3, '5 places restantes sur 8'],
    ['fr', 7, '1 place restante sur 8'],
    ['en', 3, '5 seats left of 8'],
    ['en', 7, '1 seat left of 8'],
  ])('in %s with %i taken', async (locale, accepted, shown) => {
    expect(await capacityLine(locale, accepted)).toContain(shown)
  })
})
