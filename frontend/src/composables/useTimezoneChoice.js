import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from '@/composables/useConfirm'
import { useInstanceTimezone } from '@/composables/useInstanceTimezone'
import { getLocale } from '@/i18n'
import {
  browserZone,
  buildRows,
  clockAt,
  lineKey,
  rowOfFirst,
  zoneToSave,
} from '@/utils/instanceTimezone'

const CLOCK_REFRESH_MS = 30_000

/** The list of time zones and the row picked in it: settings page and setup wizard. */
export function useTimezoneChoice() {
  const { t } = useI18n()
  const confirm = useConfirm()
  const { status, load, save } = useInstanceTimezone()

  const selectedKey = ref('')
  const rows = computed(() =>
    buildRows(status.value?.groups ?? [], {
      lineName: key => t(lineKey(key)),
      utcName: t('settings.timezoneUtc'),
      locale: getLocale(),
    }),
  )
  const selectedRow = computed(() => rows.value.find(row => row.key === selectedKey.value))
  const savedRow = computed(() => rowOfFirst(rows.value, [status.value?.timezone]))
  const canSave = computed(() => Boolean(selectedRow.value) && selectedRow.value !== savedRow.value)

  async function loadChoice() {
    await load()
    if (!status.value) return
    const first = rowOfFirst(rows.value, [
      status.value.timezone,
      browserZone(),
      status.value.effective,
    ])
    selectedKey.value = first?.key ?? ''
  }

  const confirmChoice = () =>
    confirm({
      title: t('settings.timezoneConfirmTitle'),
      message: t('settings.timezoneConfirmMessage', { zone: selectedRow.value.label }),
      variant: 'warn',
      confirmLabel: t('common.save'),
      cancelLabel: t('common.cancel'),
    })

  const saveChoice = () => save(zoneToSave(selectedRow.value, browserZone()))

  return {
    status,
    selectedKey,
    rows,
    selectedRow,
    savedRow,
    canSave,
    loadChoice,
    confirmChoice,
    saveChoice,
  }
}

/** Time in ``row`` (a ref to a row), kept fresh while the calling component is mounted. */
export function useTimezoneClock(row) {
  const now = ref(new Date())
  const timer = setInterval(() => {
    now.value = new Date()
  }, CLOCK_REFRESH_MS)
  onBeforeUnmount(() => clearInterval(timer))
  return computed(() => (row.value ? clockAt(row.value.offset, getLocale(), now.value) : ''))
}
