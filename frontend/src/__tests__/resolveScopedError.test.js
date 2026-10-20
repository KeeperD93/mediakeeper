/**
 * A screen's own error message comes first when its locale scope has one;
 * bare statuses and other codes go through the shared resolution.
 */
import { describe, it, expect, vi } from 'vitest'

// Fake translations: an unknown key comes back unchanged, as with vue-i18n.
const MESSAGES = vi.hoisted(() => ({
  'portal.lists.errors.list_full': 'This list is full.',
  'requestsAdmin.users.errors.http_500': 'Emby internal error (500).',
  'common.apiError.unknown': 'Error {status}',
  'common.apiError.saveFailed': 'Save failed.',
  'common.apiError.validation_failed': 'Invalid input.',
}))

vi.mock('@/i18n', () => ({
  default: {
    global: { t: (key, named) => MESSAGES[key]?.replace('{status}', named?.status) ?? key },
  },
}))

import { resolveScopedError } from '@/composables/useApi'

describe('resolveScopedError', () => {
  it("gives the screen's own message for a code its scope words", () => {
    expect(
      resolveScopedError('portal.lists.errors', 'list_full', 'common.apiError.saveFailed'),
    ).toBe('This list is full.')
  })

  it('names the failed action for a code the scope does not word', () => {
    expect(resolveScopedError('portal.lists.errors', 'gone', 'common.apiError.saveFailed')).toBe(
      'Save failed.',
    )
  })

  it('hands any other code to the shared messages before the fallback', () => {
    expect(
      resolveScopedError('portal.lists.errors', 'validation_failed', 'common.apiError.saveFailed'),
    ).toBe('Invalid input.')
  })

  it('never reads a bare status from the scope', () => {
    expect(resolveScopedError('requestsAdmin.users.errors', 'http_500')).toBe('Error 500')
  })
})
