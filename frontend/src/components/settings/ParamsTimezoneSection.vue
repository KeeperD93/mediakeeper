<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('settings.timezoneTitle') }}</h3>
    <p class="params-section-desc">{{ $t('settings.timezoneDesc') }}</p>
    <template v-if="status">
      <p v-if="!savedRow" class="params-tz-state">{{ $t('settings.timezoneNotSet') }}</p>
      <div class="params-tz-form">
        <select
          v-model="selectedKey"
          class="params-control mk-select-chevron"
          :aria-label="$t('settings.timezoneTitle')"
        >
          <option v-for="row in rows" :key="row.key" :value="row.key">{{ row.label }}</option>
        </select>
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
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MkButton from '@/components/common/MkButton.vue'
import { useTimezoneChoice, useTimezoneClock } from '@/composables/useTimezoneChoice'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const { t } = useI18n()
const { showToast } = useToast()
const {
  status,
  selectedKey,
  rows,
  selectedRow,
  savedRow,
  canSave,
  loadChoice,
  confirmChoice,
  saveChoice,
} = useTimezoneChoice()
const clock = useTimezoneClock(selectedRow)

const saving = ref(false)

async function onSave() {
  if (!(await confirmChoice())) return
  saving.value = true
  const saved = await saveChoice()
  saving.value = false
  if (saved) showToast(t('settings.timezoneSaved'), TOAST_TYPE.OK)
}

onMounted(loadChoice)
</script>

<style scoped>
.params-tz-state {
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
}
.params-tz-form {
  display: grid;
  /* As wide as the longest line of the list, and never wider than the page. */
  grid-template-columns: minmax(0, max-content);
  gap: var(--space-2);
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
