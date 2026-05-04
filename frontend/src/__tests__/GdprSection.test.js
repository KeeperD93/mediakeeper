/**
 * Vitest coverage for the admin GDPR section.
 *
 * The toggle persists immediately, the editors / DPO / delay use a
 * Save button. The pending-deletion table loads only when the toggle
 * is on. We stub HelpEditor + GdprPendingTable so the tests stay fast
 * and focused on the orchestration logic in GdprSection.vue.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

const fetchSettings = vi.fn()
const saveSettings = vi.fn()
const fetchPendingDeletions = vi.fn()
const cancelDeletionRequest = vi.fn()

vi.mock('@/composables/portal/useGdprAdmin', () => ({
  DEFAULT_SETTINGS: {
    enabled: false,
    privacy_text_fr: '',
    privacy_text_en: '',
    dpo_contact: '',
    account_purge_delay_days: 30,
  },
  useGdprAdmin: () => ({
    // Real refs so the template auto-unwraps them — a plain object
    // would stay truthy and keep the Save button disabled forever.
    saving: ref(false),
    error: ref(null),
    fetchSettings,
    saveSettings,
    fetchPendingDeletions,
    cancelDeletionRequest,
  }),
}))

// HelpEditor pulls TipTap which is heavy and not under test here.
vi.mock('@/components/portal/help/HelpEditor.vue', () => ({
  default: {
    name: 'HelpEditorStub',
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template:
      '<textarea class="help-editor-stub" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
}))

import GdprSection from '@/components/portal/admin/GdprSection.vue'

beforeEach(() => {
  fetchSettings.mockReset()
  saveSettings.mockReset()
  fetchPendingDeletions.mockReset()
  cancelDeletionRequest.mockReset()
})

describe('GdprSection', () => {
  it('does not render the config zone when the toggle is off', async () => {
    fetchSettings.mockResolvedValueOnce({
      enabled: false,
      privacy_text_fr: '',
      privacy_text_en: '',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    const w = mount(GdprSection)
    await flushPromises()

    expect(w.find('.pt-gdpr-config').exists()).toBe(false)
    expect(fetchPendingDeletions).not.toHaveBeenCalled()
  })

  it('renders the config zone and loads pending users when toggle is on', async () => {
    fetchSettings.mockResolvedValueOnce({
      enabled: true,
      privacy_text_fr: '<p>fr</p>',
      privacy_text_en: '<p>en</p>',
      dpo_contact: 'op@example.org',
      account_purge_delay_days: 30,
    })
    fetchPendingDeletions.mockResolvedValueOnce([])
    const w = mount(GdprSection)
    await flushPromises()

    expect(w.find('.pt-gdpr-config').exists()).toBe(true)
    expect(fetchPendingDeletions).toHaveBeenCalledOnce()
    // Two TipTap stubs, one per language.
    expect(w.findAll('.help-editor-stub')).toHaveLength(2)
  })

  it('persists the toggle change immediately (PUT enabled=true)', async () => {
    fetchSettings.mockResolvedValueOnce({
      enabled: false,
      privacy_text_fr: '',
      privacy_text_en: '',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    saveSettings.mockResolvedValueOnce({
      enabled: true,
      privacy_text_fr: '',
      privacy_text_en: '',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    fetchPendingDeletions.mockResolvedValueOnce([])
    const w = mount(GdprSection)
    await flushPromises()

    const cb = w.find('.pt-gdpr-toggle-input')
    cb.element.checked = true
    await cb.trigger('change')
    await flushPromises()

    expect(saveSettings).toHaveBeenCalledWith({ enabled: true })
    // Pending list pulls in once the toggle is on.
    expect(fetchPendingDeletions).toHaveBeenCalled()
  })

  it('disables the Save button when the delay is below the floor', async () => {
    fetchSettings.mockResolvedValueOnce({
      enabled: true,
      privacy_text_fr: '',
      privacy_text_en: '',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    fetchPendingDeletions.mockResolvedValueOnce([])
    const w = mount(GdprSection)
    await flushPromises()

    const delayInput = w.find('input[type="number"]')
    await delayInput.setValue(3)
    await flushPromises()

    const saveBtn = w.find('.pt-gdpr-save')
    expect(saveBtn.attributes('disabled')).toBeDefined()
    // Inline validation surfaces.
    expect(w.find('.pt-gdpr-error').exists()).toBe(true)
  })

  it('disables the Save button when the delay is above the cap', async () => {
    fetchSettings.mockResolvedValueOnce({
      enabled: true,
      privacy_text_fr: '',
      privacy_text_en: '',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    fetchPendingDeletions.mockResolvedValueOnce([])
    const w = mount(GdprSection)
    await flushPromises()

    await w.find('input[type="number"]').setValue(120)
    await flushPromises()

    expect(w.find('.pt-gdpr-save').attributes('disabled')).toBeDefined()
  })

  it('persists privacy texts + DPO + delay through Save', async () => {
    fetchSettings.mockResolvedValueOnce({
      enabled: true,
      privacy_text_fr: '<p>fr</p>',
      privacy_text_en: '<p>en</p>',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    fetchPendingDeletions.mockResolvedValueOnce([])
    saveSettings.mockResolvedValueOnce({
      enabled: true,
      privacy_text_fr: '<p>fr</p>',
      privacy_text_en: '<p>en</p>',
      dpo_contact: 'dpo@example.org',
      account_purge_delay_days: 45,
    })
    const w = mount(GdprSection)
    await flushPromises()

    // DPO field — first text input above the number field.
    const dpoInput = w.find('input[type="text"]')
    await dpoInput.setValue('dpo@example.org')
    await w.find('input[type="number"]').setValue(45)
    await w.find('.pt-gdpr-save').trigger('click')
    await flushPromises()

    expect(saveSettings).toHaveBeenCalledWith({
      privacy_text_fr: '<p>fr</p>',
      privacy_text_en: '<p>en</p>',
      dpo_contact: 'dpo@example.org',
      account_purge_delay_days: 45,
    })
  })

  it('flips the form back when the toggle is switched off', async () => {
    fetchSettings.mockResolvedValueOnce({
      enabled: true,
      privacy_text_fr: '',
      privacy_text_en: '',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    fetchPendingDeletions.mockResolvedValueOnce([
      { id: 1, username: 'pending-user', deletion_requested_at: '', pending_deletion_at: '' },
    ])
    saveSettings.mockResolvedValueOnce({
      enabled: false,
      privacy_text_fr: '',
      privacy_text_en: '',
      dpo_contact: '',
      account_purge_delay_days: 30,
    })
    const w = mount(GdprSection)
    await flushPromises()

    expect(w.find('.pt-gdpr-config').exists()).toBe(true)

    const cb = w.find('.pt-gdpr-toggle-input')
    cb.element.checked = false
    await cb.trigger('change')
    await flushPromises()

    expect(saveSettings).toHaveBeenCalledWith({ enabled: false })
    expect(w.find('.pt-gdpr-config').exists()).toBe(false)
  })
})
