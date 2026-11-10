/**
 * The "Action required" category comes first, with its own icon and colour class.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ChangelogView from '@/views/ChangelogView.vue'

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet: vi.fn().mockResolvedValue({
      app_version: '1.2.3',
      versions: [
        {
          version: '1.2.3',
          date: '2026-01-01',
          admin: { Action: ['Test action'], Added: ['Test addition'] },
          portal: null,
        },
      ],
    }),
    apiPost: vi.fn().mockResolvedValue({}),
  }),
}))

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key, locale: { value: 'en' } }),
}))

describe('ChangelogView, Action category', () => {
  it('leads the version with the warning icon and class', async () => {
    const wrapper = mount(ChangelogView, { global: { stubs: { MkSpinner: true } } })
    await flushPromises()

    const [first, second] = wrapper.findAll('.cl-category')
    expect(first.find('.cl-cat-icon').text()).toBe('⚠️')
    expect(first.find('.cl-cat-label').classes()).toContain('cat-action')
    expect(first.find('.cl-cat-label').text()).toBe('changelog.cat.action')
    expect(first.find('.cl-item').text()).toBe('Test action')
    expect(second.find('.cl-cat-label').classes()).toContain('cat-added')
  })
})
