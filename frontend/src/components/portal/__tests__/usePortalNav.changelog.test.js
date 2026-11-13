/**
 * The avatar menu's « What's new » entry: the window it used to open is gone, the
 * new version lives in the daily digest, so the entry leads to the changelog page.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'

import { usePortalNav } from '@/components/portal/usePortalNav'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push, replace: vi.fn(), currentRoute: ref({ fullPath: '/portal' }) }),
}))
vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ logout: vi.fn() }) }))
vi.mock('@/composables/portal/useSearchHotkey', () => ({ useSearchHotkey: vi.fn() }))

function setup() {
  let nav
  const emit = vi.fn()
  mount(
    defineComponent({
      setup() {
        nav = usePortalNav({ activeTab: 'portal-home', showRequestsTab: false }, emit)
        return () => h('div')
      },
    }),
  )
  return { nav, emit }
}

describe("usePortalNav, the « What's new » entry", () => {
  it('closes the menu and opens the changelog page', () => {
    const { nav, emit } = setup()
    nav.toggleMenu()

    nav.goToChangelog()

    expect(push).toHaveBeenCalledWith({ name: 'portal-changelog' })
    expect(nav.menuOpen.value).toBe(false)
    expect(emit).not.toHaveBeenCalled()
  })
})
