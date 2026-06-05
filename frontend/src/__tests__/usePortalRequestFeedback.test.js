import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TOAST_TYPE } from '@/constants/toast'

const showToast = vi.fn()

vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))

// Simulate vue-i18n: a key in MISSING echoes back (untranslated), any other
// key gets a `#tr` suffix (or interpolated `used/max`) so the helper's
// "key !== translation" missing-key guard can be exercised both ways.
const MISSING = new Set(['portal.request.errors.http_500'])
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => {
      if (MISSING.has(key)) return key
      return params ? `${key}|${params.used}/${params.max}` : `${key}#tr`
    },
  }),
}))

import { usePortalRequestFeedback } from '@/composables/portal/usePortalRequestFeedback'

describe('usePortalRequestFeedback', () => {
  beforeEach(() => showToast.mockClear())

  it('shows the remaining-quota info toast on success under quota', () => {
    usePortalRequestFeedback().presentRequestResult({ success: true, quota: { used: 3, max: 5 } })
    expect(showToast).toHaveBeenCalledWith('portal.request.quotaInfo|3/5', TOAST_TYPE.OK, 4000)
  })

  it('warns when the request succeeded but hit the monthly cap', () => {
    usePortalRequestFeedback().presentRequestResult({ success: true, quota: { used: 5, max: 5 } })
    expect(showToast).toHaveBeenCalledWith('portal.request.quotaReached|5/5', TOAST_TYPE.WARN, 5000)
  })

  it('confirms a resubmission when retry_count >= 1 and no quota payload', () => {
    usePortalRequestFeedback().presentRequestResult({ success: true, retry_count: 2 })
    expect(showToast).toHaveBeenCalledWith('portal.request.resubmitSuccess#tr', TOAST_TYPE.OK)
  })

  it('falls back to common.success for an unlimited/admin success', () => {
    usePortalRequestFeedback().presentRequestResult({ success: true })
    expect(showToast).toHaveBeenCalledWith('common.success#tr', TOAST_TYPE.OK)
  })

  it('maps a known refusal code to its localized error message', () => {
    usePortalRequestFeedback().presentRequestResult(null, 'quota_exceeded')
    expect(showToast).toHaveBeenCalledWith(
      'portal.request.errors.quota_exceeded#tr',
      TOAST_TYPE.ERR,
    )
  })

  it('surfaces the raw code when no i18n entry exists', () => {
    usePortalRequestFeedback().presentRequestResult(null, 'http_500')
    expect(showToast).toHaveBeenCalledWith('http_500', TOAST_TYPE.ERR)
  })

  it('falls back to common.error when there is no code at all', () => {
    usePortalRequestFeedback().presentRequestResult(null, null)
    expect(showToast).toHaveBeenCalledWith('common.error#tr', TOAST_TYPE.ERR)
  })

  it('prefers res.detail/error when no thrown errorCode is given', () => {
    usePortalRequestFeedback().presentRequestResult({ detail: 'media_blacklisted' })
    expect(showToast).toHaveBeenCalledWith(
      'portal.request.errors.media_blacklisted#tr',
      TOAST_TYPE.ERR,
    )
  })
})
