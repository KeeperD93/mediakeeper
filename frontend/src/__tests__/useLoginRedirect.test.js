/**
 * Sign-in page, existing admin session: a temporary password is changed on the
 * dashboard first. Sent back to a page that needs the portal, the admin would be
 * refused there and return to the sign-in page, in an endless reload.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const ENTER_URL = '/api/portal/admin/requests/enter'
const REDIRECT = '/admin/portal/stats'
const replace = vi.hoisted(() => vi.fn())
const route = vi.hoisted(() => ({ query: {} }))
const mustChangePassword = vi.hoisted(() => ({ value: false }))
const fetchApiResponse = vi.hoisted(() => vi.fn())
const checkAuth = vi.hoisted(() => vi.fn())
const checkPortalAuth = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ replace }),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ checkAuth, mustChangePassword }),
}))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ checkPortalAuth }),
}))
vi.mock('@/composables/useApi', () => ({ fetchApiResponse }))

import { ref } from 'vue'
import { useLoginRedirect } from '@/composables/useLoginRedirect'

async function startSignInPage() {
  const flow = useLoginRedirect({
    username: ref(''),
    remember: ref(false),
    errorMsg: ref(''),
    loggedOutMsg: ref(''),
  })
  await flow.start()
}

function enterCalls() {
  return fetchApiResponse.mock.calls.filter(([url]) => url === ENTER_URL)
}

beforeEach(() => {
  replace.mockReset()
  route.query = { redirect: REDIRECT }
  mustChangePassword.value = false
  checkAuth.mockReset().mockResolvedValue(true)
  checkPortalAuth.mockReset()
  fetchApiResponse.mockReset().mockResolvedValue({ status: 200, ok: true })
})

describe('useLoginRedirect — existing admin session', () => {
  it('sends an admin with a temporary password to the dashboard', async () => {
    mustChangePassword.value = true

    await startSignInPage()

    expect(replace).toHaveBeenCalledExactlyOnceWith('/')
    expect(enterCalls()).toHaveLength(0)
  })

  it('honours the requested page once the password is changed', async () => {
    await startSignInPage()

    expect(enterCalls()).toHaveLength(1)
    expect(replace).toHaveBeenCalledExactlyOnceWith(REDIRECT)
  })
})

describe('useLoginRedirect — the page asked for, while the session check runs', () => {
  it.each([
    ['an admin', REDIRECT, checkAuth],
    ['a member', '/portal/requests/42', checkPortalAuth],
  ])('sends %s there though the address moves on meanwhile', async (_, asked, check) => {
    route.query = { redirect: asked }
    checkAuth.mockResolvedValue(false)
    let answer
    check.mockReturnValue(
      new Promise(resolve => {
        answer = resolve
      }),
    )
    const started = startSignInPage()
    await vi.waitFor(() => expect(check).toHaveBeenCalled())

    // A sign-in sent meanwhile has reached that page: its address has no redirect.
    route.query = {}
    answer(true)
    await started

    expect(replace).toHaveBeenLastCalledWith(asked)
  })
})
