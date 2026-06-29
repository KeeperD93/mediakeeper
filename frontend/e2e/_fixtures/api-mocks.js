// Strict, centralised API mock layer for Playwright E2E tests.
//
// Goals:
//   - Replace every real network call to /api/** with a deterministic stub.
//   - Make any unexpected /api/** call fail the test loudly, so a regression
//     that adds a new boot-time call surfaces here instead of timing out
//     against a non-existent backend.
//   - Keep payload shapes compatible with the frontend composables that
//     consume them at boot (useAuth, usePortalAuth, LoginView).
//
// No secrets, no real accounts, no real backend, no third-party hosts.

const DEFAULT_HANDLERS = [
  {
    name: 'health-ok',
    match: url => url.pathname === '/api/health',
    handler: route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      }),
  },
  {
    name: 'changelog-current',
    match: url => url.pathname === '/api/changelog/current',
    handler: route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ version: '0.0.0-e2e', entries: [] }),
      }),
  },
  {
    name: 'auth-me-anonymous',
    match: url => url.pathname === '/api/auth/me',
    handler: route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Unauthenticated' }),
      }),
  },
  {
    // The shared apiClient automatically retries any 401 from a non-refresh
    // route by POSTing /api/auth/refresh. Stub it as 401 so the auto-retry
    // path resolves cleanly without ever leaving the SPA.
    name: 'auth-refresh-anonymous',
    match: url => url.pathname === '/api/auth/refresh',
    handler: route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Unauthenticated' }),
      }),
  },
  {
    name: 'portal-auth-me-anonymous',
    match: url => url.pathname === '/api/portal/auth/me',
    handler: route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Unauthenticated' }),
      }),
  },
  {
    // LoginView checks maintenance state on mount. Stub it as "off" so the
    // banner stays hidden and the call does not fall through to the strict
    // catch-all (which would fail the unexpected-request assertion).
    name: 'portal-maintenance-off',
    match: url => url.pathname === '/api/portal/maintenance',
    handler: route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ enabled: false }),
      }),
  },
]

/**
 * Install the mock layer on a Playwright page.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {Array<{name: string, match: (url: URL) => boolean, handler: (route: import('@playwright/test').Route, request: import('@playwright/test').Request) => Promise<void>|void}>} [options.overrides]
 *   Additional handlers, evaluated before the defaults. First match wins.
 * @returns {Promise<{unexpected: Array<{method: string, url: string}>}>}
 *   Tracker that exposes any /api/** call that fell through to the strict
 *   catch-all. Tests can assert it stays empty.
 */
export async function mockApi(page, options = {}) {
  const overrides = Array.isArray(options.overrides) ? options.overrides : []
  const allHandlers = [...overrides, ...DEFAULT_HANDLERS]
  const tracker = { unexpected: [] }

  await page.route('**/api/**', (route, request) => {
    let url
    try {
      url = new URL(request.url())
    } catch {
      tracker.unexpected.push({ method: request.method(), url: request.url() })
      return route.fulfill({
        status: 599,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'mock-fallthrough: unparsable URL' }),
      })
    }

    for (const entry of allHandlers) {
      if (entry.match(url, request)) {
        return entry.handler(route, request)
      }
    }

    // Strict fallback: record the call and fail it with a clear payload.
    // The test should also assert tracker.unexpected is empty.
    tracker.unexpected.push({ method: request.method(), url: url.pathname + url.search })
    return route.fulfill({
      status: 599,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: `mock-fallthrough: ${request.method()} ${url.pathname} not stubbed`,
      }),
    })
  })

  return tracker
}

/**
 * Helper to build a JSON fulfil response.
 */
export function jsonResponse(body, status = 200) {
  return route =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
}
