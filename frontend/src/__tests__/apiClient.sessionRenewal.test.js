/**
 * fetchApiResponse after a 401: an admin session is renewed (refresh, then the
 * portal session through /enter on a portal route) and the call retried; a member
 * whose session ended is sent to the login page and gets null. The chat
 * reconnect relies on both.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchApiResponse } from '@/composables/apiClient'
import { STORAGE_KEYS } from '@/constants/storage'

const PORTAL_CALL = '/api/portal/chat/unread'

describe('fetchApiResponse — expired session', () => {
  let calls
  let fakeLocation

  function answerWith(...statuses) {
    const queue = [...statuses]
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, options) => {
        calls.push(`${options?.method || 'GET'} ${url}`)
        const status = queue.shift()
        return { status, ok: status >= 200 && status < 300 }
      }),
    )
  }

  beforeEach(() => {
    calls = []
    sessionStorage.clear()
    fakeLocation = { pathname: '/portal/requests', search: '?tab=open', href: '' }
    vi.stubGlobal('location', fakeLocation)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renews an admin portal session through /enter and retries the call', async () => {
    answerWith(401, 200, 401, 200, 200)

    const res = await fetchApiResponse(PORTAL_CALL)

    expect(res.status).toBe(200)
    expect(calls).toEqual([
      `GET ${PORTAL_CALL}`,
      'POST /api/auth/refresh',
      `GET ${PORTAL_CALL}`,
      'POST /api/portal/admin/requests/enter',
      `GET ${PORTAL_CALL}`,
    ])
    expect(fakeLocation.href).toBe('')
  })

  it('sends a member whose session ended to the login page and returns null', async () => {
    answerWith(401, 401)

    const res = await fetchApiResponse(PORTAL_CALL)

    expect(res).toBeNull()
    expect(calls).toEqual([`GET ${PORTAL_CALL}`, 'POST /api/auth/refresh'])
    expect(fakeLocation.href).toBe(
      `/login?redirect=${encodeURIComponent('/portal/requests?tab=open')}`,
    )
    expect(sessionStorage.getItem(STORAGE_KEYS.SESSION_EXPIRED)).toBe('1')
  })
})
