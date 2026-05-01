import { describe, it, expect } from 'vitest'
import { TOAST_TYPE } from '@/constants/toast'
import { MEDIA_TYPE, isMovie, isTv } from '@/constants/media'
import { REQUEST_STATUS } from '@/constants/requests'
import { TROPHY_STATUS, TROPHY_TIER } from '@/constants/achievements'
import { USER_ROLE } from '@/constants/auth'

describe('constants/toast', () => {
  it('exposes the four canonical toast types', () => {
    expect(TOAST_TYPE.OK).toBe('ok')
    expect(TOAST_TYPE.ERR).toBe('err')
    expect(TOAST_TYPE.WARN).toBe('warn')
    expect(TOAST_TYPE.MEDIA).toBe('media')
  })

  it('is frozen (prevents accidental mutation)', () => {
    expect(Object.isFrozen(TOAST_TYPE)).toBe(true)
  })
})

describe('constants/media', () => {
  it('exposes movie/tv constants aligned with the backend', () => {
    expect(MEDIA_TYPE.MOVIE).toBe('movie')
    expect(MEDIA_TYPE.TV).toBe('tv')
  })

  it('isMovie / isTv helpers work on media_type and type', () => {
    expect(isMovie({ media_type: 'movie' })).toBe(true)
    expect(isMovie({ type: 'movie' })).toBe(true)
    expect(isMovie({ media_type: 'tv' })).toBe(false)
    expect(isTv({ media_type: 'tv' })).toBe(true)
    expect(isTv({ type: 'tv' })).toBe(true)
    expect(isTv({})).toBe(false)
    expect(isMovie(null)).toBe(false)
  })
})

describe('constants/requests', () => {
  it('exposes the three request statuses', () => {
    expect(REQUEST_STATUS.PENDING).toBe('pending')
    expect(REQUEST_STATUS.APPROVED).toBe('approved')
    expect(REQUEST_STATUS.REJECTED).toBe('rejected')
  })
})

describe('constants/achievements', () => {
  it('exposes trophy statuses and tier names', () => {
    expect(TROPHY_STATUS.UNLOCKED).toBe('unlocked')
    expect(TROPHY_STATUS.LOCKED).toBe('locked')
    expect(TROPHY_TIER.BRONZE).toBe('bronze')
    expect(TROPHY_TIER.DIAMOND).toBe('diamond')
  })
})

describe('constants/auth', () => {
  it('exposes USER_ROLE.ADMIN and USER', () => {
    expect(USER_ROLE.ADMIN).toBe('admin')
    expect(USER_ROLE.USER).toBe('user')
  })
})
