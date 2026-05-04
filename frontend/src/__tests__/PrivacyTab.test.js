/**
 * Vitest coverage for the user-facing Privacy tab.
 *
 * Loads the privacy text + DPO contact on mount, opens the deletion
 * modal on click, and routes the export / submit / cancel flows
 * through ``useGdprUser``. Backend errors map to localised toasts.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  getPrivacyText: vi.fn(),
  exportMyData: vi.fn(),
  submitDeletion: vi.fn(),
  refreshAuth: vi.fn(),
  showToast: vi.fn(),
  // ``profile`` mirrors the readonly ref shape exposed by usePortalAuth.
  // Tests mutate ``profile.value`` to swap between Emby / local accounts.
  profile: { value: { source: 'emby' } },
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => {
      // The deletion modal compares typed input against the magic
      // word — return a deterministic value so the confirm flow can
      // be exercised end-to-end here.
      if (key === 'portal.privacy.deleteModal.magicWord') return 'SUPPRIMER'
      return params ? `${key}:${JSON.stringify(params)}` : key
    },
    locale: { value: 'fr' },
  }),
}))

vi.mock('@/composables/portal/useGdprUser', () => ({
  EXPORT_LIMIT: 'export_rate_limited',
  EXPORT_TOO_LARGE: 'export_too_large',
  useGdprUser: () => ({
    getPrivacyText: mocks.getPrivacyText,
    exportMyData: mocks.exportMyData,
    submitDeletion: mocks.submitDeletion,
  }),
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({
    profile: mocks.profile,
    refreshAuth: mocks.refreshAuth,
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: mocks.showToast }),
}))
vi.mock('@/constants/toast', () => ({
  TOAST_TYPE: { OK: 'ok', ERR: 'err' },
}))

vi.mock('lucide-vue-next', () => ({
  Download: { name: 'DownloadStub', template: '<i />' },
  Trash2: { name: 'Trash2Stub', template: '<i />' },
  AlertTriangle: { name: 'AlertTriangleStub', template: '<i />' },
}))

// DOMPurify is real but trivial — leave it as-is so the test exercises
// the actual sanitisation path.

import PrivacyTab from '@/components/portal/settings/PrivacyTab.vue'


function buildTab() {
  return mount(PrivacyTab, {
    global: {
      stubs: {
        'i18n-t': {
          template: '<span><slot name="contact"/><slot name="word"/></span>',
        },
      },
    },
  })
}


beforeEach(() => {
  mocks.getPrivacyText.mockReset()
  mocks.exportMyData.mockReset()
  mocks.submitDeletion.mockReset()
  mocks.refreshAuth.mockReset()
  mocks.showToast.mockReset()
  // Default to an Emby-linked account so the existing tests keep
  // exercising the same surface.
  mocks.profile.value = { source: 'emby' }
})


describe('PrivacyTab', () => {
  it('renders the privacy HTML returned by the backend', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr',
      text_html: '<p>Politique FR</p>',
      dpo_contact: '',
    })
    const w = buildTab()
    await flushPromises()

    expect(w.find('.pt-privacy-text').exists()).toBe(true)
    expect(w.find('.pt-privacy-text').html()).toContain('Politique FR')
    expect(w.find('.pt-privacy-empty').exists()).toBe(false)
  })

  it('renders the not-configured fallback when text is empty', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '', dpo_contact: '',
    })
    const w = buildTab()
    await flushPromises()
    expect(w.find('.pt-privacy-empty').exists()).toBe(true)
    expect(w.find('.pt-privacy-text').exists()).toBe(false)
  })

  it('shows the DPO contact when configured', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '', dpo_contact: 'dpo@example.org',
    })
    const w = buildTab()
    await flushPromises()
    expect(w.find('.pt-privacy-dpo').text()).toContain('dpo@example.org')
  })

  it('triggers the export composable on click and toasts success', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '', dpo_contact: '',
    })
    mocks.exportMyData.mockResolvedValueOnce({ filename: 'mk.zip' })
    const w = buildTab()
    await flushPromises()

    const exportBtn = w.findAll('button.pt-settings-btn')[0]
    await exportBtn.trigger('click')
    await flushPromises()

    expect(mocks.exportMyData).toHaveBeenCalledOnce()
    expect(mocks.showToast).toHaveBeenCalledWith(
      'portal.privacy.data.exportStarted', 'ok',
    )
  })

  it('toasts a localised limit message on export 429', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '', dpo_contact: '',
    })
    const limitErr = new Error('export_rate_limited')
    limitErr.code = 'export_rate_limited'
    limitErr.retryAfter = '' // no Retry-After hint → generic message
    mocks.exportMyData.mockRejectedValueOnce(limitErr)
    const w = buildTab()
    await flushPromises()

    await w.findAll('button.pt-settings-btn')[0].trigger('click')
    await flushPromises()

    expect(mocks.showToast).toHaveBeenCalledWith(
      'portal.privacy.data.exportLimited', 'err',
    )
  })

  it('toasts a too-large error on export 413', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '', dpo_contact: '',
    })
    const tooBig = new Error('export_too_large')
    tooBig.code = 'export_too_large'
    mocks.exportMyData.mockRejectedValueOnce(tooBig)
    const w = buildTab()
    await flushPromises()

    await w.findAll('button.pt-settings-btn')[0].trigger('click')
    await flushPromises()

    expect(mocks.showToast).toHaveBeenCalledWith(
      'portal.privacy.data.exportTooLarge', 'err',
    )
  })

  it('opens the deletion modal on Delete click and submits on confirm', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '', dpo_contact: '',
    })
    mocks.submitDeletion.mockResolvedValueOnce({ ok: true, alreadyPending: false })
    mocks.refreshAuth.mockResolvedValueOnce(true)
    const w = buildTab()
    await flushPromises()

    // The Delete button is the second .pt-settings-btn in the actions row.
    await w.findAll('button.pt-settings-btn')[1].trigger('click')
    await flushPromises()
    expect(w.find('.pt-dcm-panel').exists()).toBe(true)

    // Drive the modal: type the magic word, click confirm.
    await w.find('.pt-dcm-input').setValue('SUPPRIMER')
    await w.find('.pt-dcm-btn--danger').trigger('click')
    await flushPromises()

    expect(mocks.submitDeletion).toHaveBeenCalledOnce()
    expect(mocks.refreshAuth).toHaveBeenCalledOnce()
    expect(mocks.showToast).toHaveBeenCalledWith(
      'portal.privacy.deleteModal.scheduled', 'ok',
    )
  })

  it('closes the modal silently when the backend reports already_pending', async () => {
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '', dpo_contact: '',
    })
    mocks.submitDeletion.mockResolvedValueOnce({ ok: true, alreadyPending: true })
    mocks.refreshAuth.mockResolvedValueOnce(true)
    const w = buildTab()
    await flushPromises()

    await w.findAll('button.pt-settings-btn')[1].trigger('click')
    await flushPromises()
    await w.find('.pt-dcm-input').setValue('SUPPRIMER')
    await w.find('.pt-dcm-btn--danger').trigger('click')
    await flushPromises()

    // No success toast — the visual answer is the banner appearing.
    expect(mocks.showToast).not.toHaveBeenCalledWith(
      'portal.privacy.deleteModal.scheduled', 'ok',
    )
    expect(mocks.refreshAuth).toHaveBeenCalledOnce()
  })

  it('renders the Emby notice for an Emby-sourced account', async () => {
    mocks.profile.value = { source: 'emby' }
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '<p>x</p>', dpo_contact: '',
    })
    const w = buildTab()
    await flushPromises()

    expect(w.find('.pt-privacy-emby-final').exists()).toBe(true)
    expect(w.find('.pt-privacy-emby-final').text())
      .toContain('portal.privacy.embyNotice')
  })

  it('hides the Emby notice for a locally-sourced account', async () => {
    mocks.profile.value = { source: 'local' }
    mocks.getPrivacyText.mockResolvedValueOnce({
      lang: 'fr', text_html: '<p>x</p>', dpo_contact: '',
    })
    const w = buildTab()
    await flushPromises()

    expect(w.find('.pt-privacy-emby-final').exists()).toBe(false)
  })
})
