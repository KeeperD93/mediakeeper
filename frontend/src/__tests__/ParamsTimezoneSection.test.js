/**
 * Settings → General → time zone: one list from the negative offsets to the positive
 * ones, pre-selected from the saved zone or the browser, search in every zone, saved
 * only after a confirmation.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const status = ref(null)
const load = vi.fn()
const save = vi.fn()
const confirm = vi.fn()
const showToast = vi.fn()
vi.mock('@/composables/useInstanceTimezone', () => ({
  useInstanceTimezone: () => ({ status, load, save }),
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => confirm }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, named) => {
      if (key.startsWith('settings.timezoneLine.')) return key.split('.').pop()
      return named?.zone ? `${key}:${named.zone}` : key
    },
  }),
}))
vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))
vi.mock('@/utils/instanceTimezone', async importOriginal => ({
  ...(await importOriginal()),
  browserZone: () => 'Asia/Tokyo',
}))

import ParamsTimezoneSection from '@/components/settings/ParamsTimezoneSection.vue'
import { TOAST_TYPE } from '@/constants/toast'

// As the server sends them: sorted by offset, one group per way of counting days.
const GROUPS = [
  { offset: -300, zones: ['America/New_York', 'America/Toronto'] },
  { offset: 0, zones: ['UTC'] },
  { offset: 60, zones: ['Europe/Berlin', 'Europe/Paris', 'Europe/Tirane'] },
  { offset: 345, zones: ['Asia/Kathmandu'] },
  { offset: 540, zones: ['Asia/Seoul', 'Asia/Tokyo'] },
  { offset: 660, zones: ['Pacific/Norfolk'] },
  { offset: 720, zones: ['Pacific/Fiji'] },
]
const NOT_SAVED = { timezone: null, effective: 'UTC', groups: GROUPS }
const SAVED = { timezone: 'Europe/Paris', effective: 'Europe/Paris', groups: GROUPS }
const LABELS = {
  eastern: '(UTC-05:00) Eastern',
  utc: '(UTC) settings.timezoneUtc',
  amsterdam: '(UTC+01:00) Amsterdam',
  brussels: '(UTC+01:00) Brussels',
  kathmandu: '(UTC+05:45) Kathmandu',
  seoul: '(UTC+09:00) Seoul',
  tokyo: '(UTC+09:00) Tokyo',
  norfolk: '(UTC+11:00) Norfolk',
  fiji: '(UTC+12:00) Fiji',
}

async function mountWith(value) {
  load.mockImplementation(async () => {
    status.value = value
  })
  const wrapper = mount(ParamsTimezoneSection, {
    global: {
      stubs: {
        MkButton: {
          props: ['disabled', 'loading'],
          emits: ['click'],
          template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
        },
      },
    },
  })
  await flushPromises()
  return wrapper
}

const menu = w => w.get('select')
const shownLabels = w =>
  menu(w)
    .findAll('option')
    .map(option => option.text())
const selectedLabel = w => menu(w).element.selectedOptions[0]?.text
const search = (w, text) => w.get('input[type="search"]').setValue(text)

describe('ParamsTimezoneSection', () => {
  beforeEach(() => {
    status.value = null
    load.mockReset()
    save.mockReset().mockResolvedValue(true)
    confirm.mockReset().mockResolvedValue(true)
    showToast.mockClear()
  })

  it('lists the lines of the list, from the negative offsets to the positive', async () => {
    const w = await mountWith(NOT_SAVED)
    expect(shownLabels(w)).toEqual([
      LABELS.eastern,
      LABELS.utc,
      LABELS.amsterdam,
      LABELS.brussels,
      LABELS.kathmandu,
      LABELS.seoul,
      LABELS.tokyo,
      LABELS.fiji,
    ])
    expect(w.findAll('optgroup')).toHaveLength(0)
  })

  it('uses the shared menu arrow', async () => {
    const w = await mountWith(NOT_SAVED)
    expect(menu(w).classes()).toContain('mk-select-chevron')
  })

  it('offers the row of the browser and says nothing is saved yet', async () => {
    const w = await mountWith(NOT_SAVED)
    expect(selectedLabel(w)).toBe(LABELS.tokyo)
    expect(w.text()).toContain('settings.timezoneNotSet')
    expect(w.get('button').attributes('disabled')).toBeUndefined()
  })

  it('starts on the row of the saved zone, with nothing to save', async () => {
    const w = await mountWith(SAVED)
    expect(selectedLabel(w)).toBe(LABELS.brussels)
    expect(w.text()).toContain('settings.timezoneCurrent')
    expect(w.text()).toContain(LABELS.brussels)
    expect(w.get('button').attributes('disabled')).toBeDefined()
  })

  it('starts on the first line of its group for a saved zone on no line', async () => {
    const w = await mountWith({ ...SAVED, timezone: 'Europe/Tirane', effective: 'Europe/Tirane' })
    expect(selectedLabel(w)).toBe(LABELS.amsterdam)
    expect(w.get('button').attributes('disabled')).toBeDefined()
  })

  it('keeps a saved row on no line in the list', async () => {
    const norfolk = 'Pacific/Norfolk'
    const w = await mountWith({ ...SAVED, timezone: norfolk, effective: norfolk })
    expect(selectedLabel(w)).toBe(LABELS.norfolk)
    expect(shownLabels(w)[0]).toBe(LABELS.norfolk)
  })

  it('searches every zone, also those no row names, and keeps the selection', async () => {
    const w = await mountWith(SAVED)
    await search(w, 'fiji')
    expect(shownLabels(w)).toEqual([LABELS.brussels, LABELS.fiji])
    expect(selectedLabel(w)).toBe(LABELS.brussels)
    await search(w, 'tirane')
    expect(shownLabels(w)).toEqual([LABELS.brussels, LABELS.amsterdam])
    await search(w, 'norfolk')
    expect(shownLabels(w)).toEqual([LABELS.brussels, LABELS.norfolk])
  })

  it('sorts the search results by offset too', async () => {
    const w = await mountWith(SAVED)
    await search(w, 'a')
    expect(shownLabels(w)).toEqual([
      LABELS.eastern,
      LABELS.amsterdam,
      LABELS.brussels,
      LABELS.kathmandu,
      LABELS.seoul,
      LABELS.tokyo,
      LABELS.norfolk,
      LABELS.fiji,
    ])
  })

  it('says when no zone matches the search', async () => {
    const w = await mountWith(SAVED)
    await search(w, 'atlantis')
    expect(w.text()).toContain('settings.timezoneNoMatch')
    expect(shownLabels(w)).toEqual([LABELS.brussels])
  })

  it('shows the time in the selected row', async () => {
    const w = await mountWith(SAVED)
    expect(w.text()).toContain('settings.timezoneClock')
  })

  it('saves the city of the browser when its row is chosen', async () => {
    const w = await mountWith(NOT_SAVED)
    await w.get('button').trigger('click')
    await flushPromises()
    expect(confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        message: `settings.timezoneConfirmMessage:${LABELS.tokyo}`,
        variant: 'warn',
      }),
    )
    expect(save).toHaveBeenCalledWith('Asia/Tokyo')
    expect(showToast).toHaveBeenCalledWith('settings.timezoneSaved', TOAST_TYPE.OK)
  })

  it('saves the first zone of another row', async () => {
    const w = await mountWith(NOT_SAVED)
    await menu(w).setValue('Amsterdam')
    await w.get('button').trigger('click')
    await flushPromises()
    expect(save).toHaveBeenCalledWith('Europe/Berlin')
  })

  it('saves nothing when the confirmation is refused', async () => {
    confirm.mockResolvedValue(false)
    const w = await mountWith(NOT_SAVED)
    await w.get('button').trigger('click')
    await flushPromises()
    expect(save).not.toHaveBeenCalled()
    expect(showToast).not.toHaveBeenCalled()
  })

  it('announces no success when the server refuses', async () => {
    save.mockResolvedValue(false)
    const w = await mountWith(NOT_SAVED)
    await w.get('button').trigger('click')
    await flushPromises()
    expect(showToast).not.toHaveBeenCalled()
  })

  it('shows only its title when the status cannot be read', async () => {
    const w = await mountWith(null)
    expect(w.find('select').exists()).toBe(false)
    expect(w.text()).toContain('settings.timezoneTitle')
  })

  it('stops refreshing the clock once closed', async () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval')
    const w = await mountWith(SAVED)
    w.unmount()
    expect(clearSpy).toHaveBeenCalled()
    clearSpy.mockRestore()
  })
})
