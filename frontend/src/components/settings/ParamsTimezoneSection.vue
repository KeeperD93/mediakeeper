<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('settings.timezoneTitle') }}</h3>
    <p class="params-section-desc">{{ $t('settings.timezoneDesc') }}</p>
    <template v-if="status">
      <p class="params-tz-state">
        {{
          status.timezone
            ? $t('settings.timezoneCurrent', { zone: currentLabel })
            : $t('settings.timezoneNotSet')
        }}
      </p>
      <div class="params-tz-form">
        <input
          v-model="search"
          type="search"
          class="params-control params-tz-search"
          :placeholder="$t('settings.timezoneSearch')"
          :aria-label="$t('settings.timezoneSearch')"
        />
        <select
          v-model="selectedKey"
          class="params-control mk-select-chevron"
          :aria-label="$t('settings.timezoneTitle')"
        >
          <option v-for="row in listedRows" :key="row.key" :value="row.key">{{ row.label }}</option>
        </select>
        <p v-if="matches && !matches.length" class="params-tz-hint">
          {{ $t('settings.timezoneNoMatch') }}
        </p>
        <div class="params-tz-actions">
          <MkButton class="mk-touch-mobile" :disabled="!canSave" :loading="saving" @click="onSave">
            {{ $t('common.save') }}
          </MkButton>
          <p v-if="clock" class="params-tz-hint">
            {{ $t('settings.timezoneClock', { time: clock }) }}
          </p>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MkButton from '@/components/common/MkButton.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useInstanceTimezone } from '@/composables/useInstanceTimezone'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { getLocale } from '@/i18n'
import {
  browserZone,
  buildRows,
  clockAt,
  lineKey,
  matchRows,
  rowOfFirst,
  zoneToSave,
} from '@/utils/instanceTimezone'

const CLOCK_REFRESH_MS = 30_000

const { t } = useI18n()
const confirm = useConfirm()
const { showToast } = useToast()
const { status, load, save } = useInstanceTimezone()

const selectedKey = ref('')
const search = ref('')
const saving = ref(false)
const now = ref(new Date())
const clockTimer = setInterval(() => {
  now.value = new Date()
}, CLOCK_REFRESH_MS)

const rows = computed(() =>
  buildRows(status.value?.groups ?? [], {
    lineName: key => t(lineKey(key)),
    utcName: t('settings.timezoneUtc'),
    locale: getLocale(),
  }),
)
const currentLabel = computed(
  () => rowOfFirst(rows.value, [status.value?.effective])?.label ?? status.value?.effective,
)
const selectedRow = computed(() => rows.value.find(row => row.key === selectedKey.value))
const savedRow = computed(() => rowOfFirst(rows.value, [status.value?.timezone]))
const matches = computed(() => (search.value.trim() ? matchRows(rows.value, search.value) : null))
const listedRows = computed(() => {
  const listed = matches.value ?? rows.value.filter(row => row.isMain)
  // A select cannot show a value it has no option for.
  return !selectedRow.value || listed.includes(selectedRow.value)
    ? listed
    : [selectedRow.value, ...listed]
})
const canSave = computed(() => Boolean(selectedRow.value) && selectedRow.value !== savedRow.value)
const clock = computed(() =>
  selectedRow.value ? clockAt(selectedRow.value.offset, getLocale(), now.value) : '',
)

async function onSave() {
  const confirmed = await confirm({
    title: t('settings.timezoneConfirmTitle'),
    message: t('settings.timezoneConfirmMessage', { zone: selectedRow.value.label }),
    variant: 'warn',
    confirmLabel: t('common.save'),
    cancelLabel: t('common.cancel'),
  })
  if (!confirmed) return
  saving.value = true
  const saved = await save(zoneToSave(selectedRow.value, browserZone()))
  saving.value = false
  if (saved) {
    search.value = ''
    showToast(t('settings.timezoneSaved'), TOAST_TYPE.OK)
  }
}

onMounted(async () => {
  await load()
  if (!status.value) return
  const first = rowOfFirst(rows.value, [
    status.value.timezone,
    browserZone(),
    status.value.effective,
  ])
  selectedKey.value = first?.key ?? ''
})
onBeforeUnmount(() => clearInterval(clockTimer))
</script>

<style scoped>
.params-tz-state {
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
}
.params-tz-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-2);
  max-width: var(--container-narrow);
}
.params-tz-search {
  padding-right: var(--space-3);
}
.params-tz-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.params-tz-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
