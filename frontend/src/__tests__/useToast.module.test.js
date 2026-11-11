/**
 * The toast header names the admin page the toast was raised on, from the
 * page's own title; outside the admin shell (portal, sign-in) it stays generic.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { setToastRouter, useToast } from '@/composables/useToast'
import { adminRoutes } from '@/router/routes/admin'
import { portalRoutes } from '@/router/routes/portal'
import fr from '@/locales/fr.json'
import en from '@/locales/en.json'

const GENERIC = 'toastModule.app'
const Page = { render: () => null }
const withPage = routes => routes.map(route => ({ ...route, component: Page }))
const label = (messages, key) => key.split('.').reduce((node, part) => node?.[part], messages)

// The real admin and portal route lists, under the same parents as the app's router.
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/login', component: Page, meta: { public: true, titleKey: 'login.title' } },
    { path: '/', component: Page, children: withPage(adminRoutes) },
    { path: '/portal', component: Page, children: withPage(portalRoutes) },
  ],
})

describe('useToast — the header of a toast', () => {
  const { toasts, showToast, removeToast } = useToast()

  const headerOn = async path => {
    await router.push(path)
    showToast('Saved', 'ok')
    return toasts.value.at(-1).module
  }

  beforeEach(() => {
    vi.useFakeTimers()
    setToastRouter(router)
  })

  afterEach(() => {
    toasts.value.forEach(toast => removeToast(toast.id))
    vi.useRealTimers()
  })

  it.each(adminRoutes.map(route => `/${route.path}`))('names the admin page %s', async path => {
    const key = await headerOn(path)

    expect(key).not.toBe(GENERIC)
    expect(label(fr, key)).toMatch(/\S/)
    expect(label(en, key)).toMatch(/\S/)
  })

  it('stays generic on the portal and the sign-in page', async () => {
    expect(await headerOn('/portal')).toBe(GENERIC)
    expect(await headerOn('/portal/requests')).toBe(GENERIC)
    expect(await headerOn('/login')).toBe(GENERIC)
  })
})
