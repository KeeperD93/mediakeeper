/**
 * Sign-in page, no session: the remembered name fills an empty field only. A
 * password manager may have filled the form during the startup checks, and
 * replacing just its name would pair it with another account's password.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: vi.fn() }),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ checkAuth: async () => false, mustChangePassword: { value: false } }),
}))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ checkPortalAuth: async () => false }),
}))
vi.mock('@/composables/useApi', () => ({
  fetchApiResponse: async () => ({ status: 200, ok: true, json: async () => ({}) }),
}))

import { ref } from 'vue'
import { STORAGE_KEYS } from '@/constants/storage'
import { useLoginRedirect } from '@/composables/useLoginRedirect'

async function startSignInPage(typedName = '') {
  const username = ref(typedName)
  const remember = ref(false)
  await useLoginRedirect({ username, remember, errorMsg: ref(''), loggedOutMsg: ref('') }).start()
  return { username: username.value, remember: remember.value }
}

describe('useLoginRedirect — remembered name', () => {
  beforeEach(() => localStorage.setItem(STORAGE_KEYS.SAVED_USERNAME, 'Alice'))
  afterEach(() => localStorage.removeItem(STORAGE_KEYS.SAVED_USERNAME))

  it('fills an empty name field and ticks the remember box', async () => {
    expect(await startSignInPage()).toEqual({ username: 'Alice', remember: true })
  })

  it('keeps a name already filled by the browser', async () => {
    expect(await startSignInPage('Bob')).toEqual({ username: 'Bob', remember: true })
  })

  it('leaves the form alone when no name is remembered', async () => {
    localStorage.removeItem(STORAGE_KEYS.SAVED_USERNAME)

    expect(await startSignInPage()).toEqual({ username: '', remember: false })
  })
})
