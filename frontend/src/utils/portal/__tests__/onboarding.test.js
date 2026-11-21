import { describe, expect, it } from 'vitest'
import { avatarFileProblem, daysUntil, initialOf } from '@/utils/portal/onboarding'
import { AVATAR_EXTENSIONS, AVATAR_MAX_BYTES, AVATAR_TYPES } from '@/constants/portalOnboarding'

const LIMITS = { types: AVATAR_TYPES, extensions: AVATAR_EXTENSIONS, maxBytes: AVATAR_MAX_BYTES }
const file = (name, type, size = 10) => ({ name, type, size })

describe('first-login wizard helpers', () => {
  it('counts calendar days, whatever the hour', () => {
    const now = new Date(2026, 10, 13, 23, 30)
    expect(daysUntil(new Date(2026, 10, 13, 8).toISOString(), now)).toBe(0)
    expect(daysUntil(new Date(2026, 10, 14, 1).toISOString(), now)).toBe(1)
    expect(daysUntil(new Date(2026, 11, 12, 12).toISOString(), now)).toBe(29)
  })

  it('takes a whole first character, upper-cased', () => {
    expect(initialOf(' alice')).toBe('A')
    expect(initialOf('éloi')).toBe('É')
    expect(initialOf('🎬 Test Movie')).toBe('🎬')
    expect(initialOf('')).toBe('')
  })

  it('checks a picked image like the server: type, extension, 5 MB', () => {
    expect(avatarFileProblem(file('me.png', 'image/png'), LIMITS)).toBeNull()
    expect(avatarFileProblem(file('me.JPEG', 'image/jpeg'), LIMITS)).toBeNull()
    expect(avatarFileProblem(file('me.svg', 'image/svg+xml'), LIMITS)).toBe('type')
    expect(avatarFileProblem(file('me', 'image/png'), LIMITS)).toBe('type')
    expect(avatarFileProblem(file('me.gif', 'image/gif', AVATAR_MAX_BYTES + 1), LIMITS)).toBe(
      'size',
    )
  })
})
