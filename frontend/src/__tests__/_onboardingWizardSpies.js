/** Spies behind the mocked composables of the first-login wizard tests (no component here:
 * the mock factories import this module). */
import { vi } from 'vitest'
import { ref } from 'vue'

export const api = {
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiFetch: vi.fn(),
}
export const auth = {
  profile: ref(null),
  replaceProfile: vi.fn(),
}
export const applyPortalLocale = vi.fn()
export const showToast = vi.fn()
