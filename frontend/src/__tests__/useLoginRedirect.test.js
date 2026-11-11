/**
 * Sign-in page, existing admin session: a temporary password is changed on the
 * dashboard first. Sent back to a page that needs the portal, the admin would be
 * refused there and return to the sign-in page, in an endless reload.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const ENTER_URL = '/api/portal/admin/requests/enter'
const REDIRECT = '/admin/portal/stats'
const replace = vi.hoisted(() => vi.fn())
const mustChangePassword = vi.hoisted(() => ({ value: false }))
const fetchApiResponse = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { redirect: REDIRECT } }),
  useRouter: () => ({ replace }),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ checkAuth: async () => true, mustChangePassword }),
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

describe('useLoginRedirect — existing admin session', () => {
  beforeEach(() => {
    replace.mockReset()
    fetchApiResponse.mockReset().mockResolvedValue({ status: 200, ok: true })
  })

  it('sends an admin with a temporary password to the dashboard', async () => {
    mustChangePassword.value = true

    await startSignInPage()

    expect(replace).toHaveBeenCalledExactlyOnceWith('/')
    expect(enterCalls()).toHaveLength(0)
  })

  it('honours the requested page once the password is changed', async () => {
    mustChangePassword.value = false

    await startSignInPage()

    expect(enterCalls()).toHaveLength(1)
    expect(replace).toHaveBeenCalledExactlyOnceWith(REDIRECT)
  })
})
