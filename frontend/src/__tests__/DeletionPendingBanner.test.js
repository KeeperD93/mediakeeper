/**
 * Vitest coverage for the GDPR grace-period banner.
 *
 * Banner is visible only when ``gdpr.pending_deletion_at`` is set on
 * the portal-auth state. Cancel triggers the user-side cancel call,
 * then refreshes /auth/me so the banner disappears reactively.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

// vi.mock factories are hoisted above plain top-level statements but
// run lazily — to share state with the test body we need vi.hoisted
// so the variables exist before the factory is evaluated. We expose
// the slot for ``gdprState`` and reassign it to a real Vue ref in
// beforeEach (ref() is unavailable this early in the lifecycle).
const mocks = vi.hoisted(() => ({
  gdprState: null,
  refreshAuth: vi.fn(),
  cancelDeletion: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
    locale: { value: 'fr' },
  }),
  // Translation is the runtime component we now import explicitly because
  // the vite plugin's ``fullInstall: false`` prevents the global ``<i18n-t>``
  // registration. Tests stub it as a transparent slot wrapper.
  Translation: { name: 'TranslationStub', template: '<span><slot name="date"/></span>' },
}))

vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({
    gdpr: mocks.gdprState,
    refreshAuth: mocks.refreshAuth,
  }),
}))

vi.mock('@/composables/portal/useGdprUser', () => ({
  useGdprUser: () => ({ cancelDeletion: mocks.cancelDeletion }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: mocks.showToast }),
}))

vi.mock('@/constants/toast', () => ({
  TOAST_TYPE: { OK: 'ok', ERR: 'err' },
}))

// Lucide icons are heavy SVGs and not under test here.
vi.mock('lucide-vue-next', () => ({
  AlertTriangle: { name: 'AlertTriangleStub', template: '<i />' },
}))

import DeletionPendingBanner from '@/components/portal/DeletionPendingBanner.vue'

function buildComponent() {
  return mount(DeletionPendingBanner, {
    global: {
      stubs: {
        // i18n-t is the vue-i18n built-in tag — mock as transparent slot.
        'i18n-t': { template: '<span><slot name="date"/></span>' },
      },
      // Teleport to body — render in a parent attached to document.
      attachTo: document.body,
    },
  })
}

beforeEach(() => {
  mocks.refreshAuth.mockReset()
  mocks.cancelDeletion.mockReset()
  mocks.showToast.mockReset()
  // Build a fresh ref every test — the component captures it once on
  // setup, so resetting the slot here gives the next mount a clean
  // reactive root.
  mocks.gdprState = ref(null)
  document.body.innerHTML = ''
})

describe('DeletionPendingBanner', () => {
  it('does not render when no deletion is pending', async () => {
    mocks.gdprState.value = { enabled: true, pending_deletion_at: null }
    const w = buildComponent()
    await flushPromises()
    expect(w.find('.pt-dpb').exists()).toBe(false)
  })

  it('renders when pending_deletion_at is set', async () => {
    mocks.gdprState.value = {
      enabled: true,
      pending_deletion_at: '2026-06-01T10:00:00Z',
    }
    const w = buildComponent()
    await flushPromises()

    expect(w.find('.pt-dpb').exists()).toBe(true)
    expect(w.find('.pt-dpb-cancel').exists()).toBe(true)
  })

  it('calls cancelDeletion + refreshAuth on cancel click', async () => {
    mocks.gdprState.value = {
      enabled: true,
      pending_deletion_at: '2026-06-01T10:00:00Z',
    }
    mocks.cancelDeletion.mockResolvedValueOnce({ status: 'cancelled' })
    mocks.refreshAuth.mockResolvedValueOnce(true)
    const w = buildComponent()
    await flushPromises()

    await w.find('.pt-dpb-cancel').trigger('click')
    await flushPromises()

    expect(mocks.cancelDeletion).toHaveBeenCalledOnce()
    expect(mocks.refreshAuth).toHaveBeenCalledOnce()
    expect(mocks.showToast).toHaveBeenCalledWith('portal.privacy.banner.cancelled', 'ok')
  })

  it('shows an error toast when cancel fails', async () => {
    mocks.gdprState.value = {
      enabled: true,
      pending_deletion_at: '2026-06-01T10:00:00Z',
    }
    mocks.cancelDeletion.mockRejectedValueOnce(new Error('boom'))
    const w = buildComponent()
    await flushPromises()

    await w.find('.pt-dpb-cancel').trigger('click')
    await flushPromises()

    expect(mocks.showToast).toHaveBeenCalledWith('portal.privacy.banner.cancelFailed', 'err')
    // refreshAuth is skipped on failure — keep the banner visible.
    expect(mocks.refreshAuth).not.toHaveBeenCalled()
  })
})
