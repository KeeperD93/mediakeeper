// The first-login wizard opening by itself over a portal page, for a fictional viewer
// whose name is free to keep.

import { expect } from '@playwright/test'
import { jsonResponse } from './api-mocks.js'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalListsHandlers,
} from './portal-auth-mocks.js'

const pathHandler = (name, pathname, body) => ({
  name,
  match: url => url.pathname === pathname,
  handler: jsonResponse(body),
})

// The viewer's name is free to keep: not locked, and judged « current » by the live check.
const WIZARD_HANDLERS = [
  pathHandler('portal-username-state', '/api/portal/profiles/me/username-state', {
    locked: false,
    locked_until: null,
    must_set: false,
    lock_days: 180,
  }),
  pathHandler('portal-check-username', '/api/portal/profiles/me/check-username', {
    available: true,
    reason: 'current',
    locked_until: null,
    suggestions: [],
  }),
]

// Opens the wizard on its welcome, without animations.
export async function openWizard(page) {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const tracker = await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, onboarding_pending: true },
    pageHandlers: [...portalListsHandlers(), ...WIZARD_HANDLERS],
  })
  await page.goto('/portal/lists')
  await expect(page.locator('.wz-step--welcome')).toBeVisible()
  return tracker
}
