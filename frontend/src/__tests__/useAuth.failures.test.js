/**
 * Sign-in and password change failures: a rate limit follows the shared rule
 * (the server's reason, else its toast), a server failure is never read as
 * "invalid credentials", and a proxy error page reads as its status. A
 * password change answered by a page that is not JSON is never a success.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/composables/handle429', async importOriginal => ({
  parseRetryAfter: (await importOriginal()).parseRetryAfter,
  rateLimitCode: vi.fn(),
}))
vi.mock('@/composables/useApi', () => ({ fetchApiResponse: vi.fn() }))

import { rateLimitCode } from '@/composables/handle429'
import { fetchApiResponse } from '@/composables/useApi'
import { useAuth } from '@/composables/useAuth'

const answer = (status, body, headers = {}) => ({
  ok: false,
  status,
  headers: new Headers(headers),
  text: async () => JSON.stringify(body),
  json: async () => body,
})

describe('useAuth — failures', () => {
  beforeEach(() => vi.clearAllMocks())

  it('a rate-limited login throws the code the shared rule gives', async () => {
    const res = answer(429, { detail: 'login_blocked' })
    fetchApiResponse.mockResolvedValue(res)
    rateLimitCode.mockReturnValue('login_blocked')

    await expect(useAuth().login('someone', 'not-a-real-password')).rejects.toThrow('login_blocked')
    expect(rateLimitCode).toHaveBeenCalledWith(res, { detail: 'login_blocked' })
  })

  it('a refused sign-in carries the wait the server gave', async () => {
    fetchApiResponse.mockResolvedValue(
      answer(429, { detail: 'login_rate_limited' }, { 'Retry-After': '42' }),
    )
    rateLimitCode.mockReturnValue('login_rate_limited')

    await expect(useAuth().login('someone', 'not-a-real-password')).rejects.toMatchObject({
      message: 'login_rate_limited',
      retryAfter: 42,
    })
  })

  it('a refused sign-in without a wait carries none', async () => {
    fetchApiResponse.mockResolvedValue(answer(429, { detail: 'login_blocked' }))
    rateLimitCode.mockReturnValue('login_blocked')

    await expect(useAuth().login('someone', 'not-a-real-password')).rejects.toMatchObject({
      message: 'login_blocked',
      retryAfter: null,
    })
  })

  it('a server failure at sign-in is not read as wrong credentials', async () => {
    fetchApiResponse.mockResolvedValue(answer(500, { error: 'internal_error' }))

    await expect(useAuth().login('someone', 'not-a-real-password')).rejects.toThrow('http_500')
  })

  it('a refused sign-in without a reason still reads as wrong credentials', async () => {
    fetchApiResponse.mockResolvedValue(answer(401, {}))

    await expect(useAuth().login('someone', 'not-a-real-password')).rejects.toThrow(
      'invalid_credentials',
    )
  })

  it('a rate-limited password change throws the code the shared rule gives', async () => {
    const res = answer(429, { error: 'Rate limit exceeded' })
    fetchApiResponse.mockResolvedValue(res)
    rateLimitCode.mockReturnValue('rate_limited_notified')

    await expect(useAuth().changePassword('old-one', 'new-one')).rejects.toThrow(
      'rate_limited_notified',
    )
    expect(rateLimitCode).toHaveBeenCalledWith(res, { error: 'Rate limit exceeded' })
  })

  it('a password change answered by a page that is not JSON is not a success', async () => {
    fetchApiResponse.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('Unexpected token <')
      },
    })

    await expect(useAuth().changePassword('old-one', 'new-one')).rejects.toThrow('unexpected')
  })

  it('a password change answered by a proxy error page reads as its status', async () => {
    fetchApiResponse.mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('Unexpected token <')
      },
    })

    await expect(useAuth().changePassword('old-one', 'new-one')).rejects.toThrow('http_502')
  })
})
