<template>
  <div class="ob-panel">
    <div class="ob-step-header">
      <div class="ob-step-icon ob-step-icon-locale">
        <Globe :size="22" :stroke-width="1.8" />
      </div>
      <div>
        <h2 class="ob-panel-title">{{ $t('onboarding.localeTitle') }}</h2>
        <p class="ob-panel-desc">{{ $t('onboarding.localeDesc') }}</p>
      </div>
    </div>

    <div class="ob-form">
      <div class="ob-field">
        <label class="ob-label" :for="languageId">{{ $t('settings.languageLabel') }}</label>
        <select
          :id="languageId"
          class="ob-select mk-select-chevron mk-touch-mobile"
          :value="currentLocale"
          @change="onLocaleChange($event.target.value)"
        >
          <option v-for="loc in AVAILABLE_LOCALES" :key="loc.code" :value="loc.code">
            {{ loc.flag }} {{ loc.label }}
          </option>
        </select>
      </div>

      <div v-if="zoneRows.length" class="ob-field">
        <label class="ob-label" :for="zoneId">{{ $t('settings.timezoneTitle') }}</label>
        <select :id="zoneId" v-model="zoneKey" class="ob-select mk-select-chevron mk-touch-mobile">
          <option v-for="row in zoneRows" :key="row.key" :value="row.key">{{ row.label }}</option>
        </select>
        <p class="ob-locale-hint">{{ $t('settings.timezoneDesc') }}</p>
        <p v-if="clock" class="ob-locale-hint">
          {{ $t('settings.timezoneClock', { time: clock }) }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, toRef, useId } from 'vue'
import { Globe } from 'lucide-vue-next'
import { useTimezoneClock } from '@/composables/useTimezoneChoice'
import { AVAILABLE_LOCALES, getLocale, setLocale } from '@/i18n'

const props = defineProps({
  zoneRows: { type: Array, required: true },
  zoneRow: { type: Object, default: undefined },
})

const zoneKey = defineModel('zoneKey', { type: String, required: true })

const languageId = useId()
const zoneId = useId()
const clock = useTimezoneClock(toRef(props, 'zoneRow'))
const currentLocale = ref(getLocale())

async function onLocaleChange(code) {
  if (await setLocale(code)) currentLocale.value = code
}
</script>

<style scoped>
.ob-step-icon-locale {
  background: rgb(var(--accent-rgb), 0.1);
  color: var(--accent-400);
}
.ob-select {
  width: 100%;
  padding-block: var(--space-2);
  padding-left: var(--space-3);
  border: var(--border-width-thin) solid var(--border);
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  transition: var(--transition-border);
}
.ob-select:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
/* iPhone zooms the page on a menu below 16px; elsewhere the wizard's size stays. */
@supports (-webkit-touch-callout: none) {
  .ob-select {
    font-size: var(--text-md);
  }
}
.ob-locale-hint {
  margin: 0;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  line-height: var(--lh-normal);
}
</style>
