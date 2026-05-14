import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EmbyMediaPicker from '@/components/portal/tickets/EmbyMediaPicker.vue'

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet,
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    apiPatch: vi.fn(),
    apiFetch: vi.fn(),
    loading: { value: false },
    error: { value: null },
  }),
}))

describe('EmbyMediaPicker', () => {
  beforeEach(() => {
    apiGet.mockReset()
    vi.useFakeTimers()
  })

  it('renders the search input when no selection', () => {
    const w = mount(EmbyMediaPicker, { props: { modelValue: null } })
    expect(w.find('.emp-input').exists()).toBe(true)
    expect(w.find('.emp-selected').exists()).toBe(false)
  })

  it('renders the selected hit summary when modelValue is set', () => {
    const w = mount(EmbyMediaPicker, {
      props: {
        modelValue: {
          id: 'emby-1',
          type: 'movie',
          title: 'Interstellar',
          poster_id: 'emby-1',
          year: '2014',
        },
      },
    })
    expect(w.find('.emp-selected').exists()).toBe(true)
    expect(w.text()).toContain('Interstellar')
    expect(w.text()).toContain('2014')
  })

  it('debounces the search and calls the autocomplete endpoint', async () => {
    apiGet.mockResolvedValueOnce({
      items: [{ id: 'mov-1', type: 'movie', title: 'Inception', poster_id: 'mov-1', year: '2010' }],
    })

    const w = mount(EmbyMediaPicker, { props: { modelValue: null } })
    const input = w.find('.emp-input')
    await input.setValue('inc')

    // The debounce window must elapse before the request fires.
    expect(apiGet).not.toHaveBeenCalled()
    vi.advanceTimersByTime(260)
    await flushPromises()

    expect(apiGet).toHaveBeenCalledOnce()
    expect(apiGet.mock.calls[0][0]).toContain('/api/portal/tickets/emby/search')
    expect(apiGet.mock.calls[0][0]).toContain('q=inc')
  })

  it('emits update:modelValue with the picked hit on click', async () => {
    apiGet.mockResolvedValueOnce({
      items: [{ id: 'mov-1', type: 'movie', title: 'Inception', poster_id: 'mov-1', year: '2010' }],
    })

    const w = mount(EmbyMediaPicker, { props: { modelValue: null } })
    await w.find('.emp-input').setValue('inc')
    vi.advanceTimersByTime(260)
    await flushPromises()

    await w.find('.emp-hit').trigger('mousedown')

    const emitted = w.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0].id).toBe('mov-1')
  })

  it('emits null when the clear button is pressed', async () => {
    const w = mount(EmbyMediaPicker, {
      props: {
        modelValue: { id: 'mov-1', type: 'movie', title: 'X', poster_id: 'mov-1' },
      },
    })
    await w.find('.emp-clear').trigger('click')
    const emitted = w.emitted('update:modelValue')
    expect(emitted[0][0]).toBeNull()
  })

  it('does not search for queries shorter than the minimum', async () => {
    const w = mount(EmbyMediaPicker, { props: { modelValue: null } })
    await w.find('.emp-input').setValue('a')
    vi.advanceTimersByTime(500)
    await flushPromises()
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('closes the dropdown on outside mousedown', async () => {
    const w = mount(EmbyMediaPicker, {
      props: { modelValue: null },
      attachTo: document.body,
    })
    await w.find('.emp-input').trigger('focus')
    expect(w.find('.emp-dropdown').exists()).toBe(true)

    // Click somewhere outside the picker root.
    const outside = document.createElement('div')
    document.body.appendChild(outside)
    outside.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    await flushPromises()

    expect(w.find('.emp-dropdown').exists()).toBe(false)
    outside.remove()
    w.unmount()
  })

  it('still selects the hit when mousedown lands on a suggestion', async () => {
    apiGet.mockResolvedValueOnce({
      items: [{ id: 'mov-1', type: 'movie', title: 'Inception', poster_id: 'mov-1', year: '2010' }],
    })
    const w = mount(EmbyMediaPicker, {
      props: { modelValue: null },
      attachTo: document.body,
    })
    await w.find('.emp-input').setValue('inc')
    vi.advanceTimersByTime(260)
    await flushPromises()

    await w.find('.emp-hit').trigger('mousedown')
    await flushPromises()

    const emitted = w.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0].id).toBe('mov-1')
    w.unmount()
  })
})
