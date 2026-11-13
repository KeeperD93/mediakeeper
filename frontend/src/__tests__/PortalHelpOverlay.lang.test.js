import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

// The Help asks the server for the portal's language: a member reads it in English
// once the portal speaks English; the editor stays on the French it edits.
const h = vi.hoisted(() => ({ load: vi.fn(), locale: null, profile: null }))

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: k => k, locale: h.locale }),
}))
vi.mock('@/composables/useFocusTrap', () => ({ useFocusTrap: () => {} }))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: h.profile }),
}))
vi.mock('@/composables/portal/usePortalHelpAdmin', () => ({
  usePortalHelpAdmin: () => ({ createArticle: vi.fn() }),
}))
vi.mock('@/composables/portal/usePortalHelp', async () => {
  const { ref: r, computed } = await import('vue')
  return {
    usePortalHelp: () => ({
      HELP_CATEGORIES: ['general'],
      loading: r(false),
      error: r(null),
      lang: r('fr'),
      search: r(''),
      activeCategory: r('general'),
      categoryCounts: computed(() => ({ general: 0 })),
      filteredArticles: computed(() => []),
      articlesInActiveCategory: computed(() => []),
      load: h.load,
      selectCategory: vi.fn(),
    }),
  }
})

import PortalHelpOverlay from '@/components/portal/PortalHelpOverlay.vue'

async function openAs(role) {
  h.profile = ref({ role })
  const w = mount(PortalHelpOverlay, {
    props: { open: false },
    global: { stubs: { HelpCardList: true, HelpEditView: true, HelpTrashView: true } },
  })
  await w.setProps({ open: true })
  await flushPromises()
  return w
}

describe('PortalHelpOverlay language', () => {
  beforeEach(() => {
    h.load.mockReset()
    h.locale = ref('en')
  })

  it('asks for the portal language for a member', async () => {
    await openAs('viewer')
    expect(h.load).toHaveBeenCalledWith('en', { admin: false })
  })

  it('leaves the editor on the default language', async () => {
    await openAs('admin')
    expect(h.load).toHaveBeenCalledWith(undefined, { admin: true })
  })
})
