<template>
  <div>
    <h2 class="params-title">{{ $t('settings.tabGeneral') }}</h2>
    <p class="params-desc">{{ $t('settings.generalDesc') }}</p>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.languageLabel') }}</h3>
      <p class="params-section-desc">{{ $t('settings.languageDesc') }}</p>
      <div class="params-lang-select-wrap">
        <select
          class="params-lang-select"
          :value="currentLocale"
          @change="onLocaleChange($event.target.value)"
        >
          <option v-for="loc in AVAILABLE_LOCALES" :key="loc.code" :value="loc.code">
            {{ loc.flag }} {{ loc.label }}
          </option>
        </select>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.updateCheckTitle') }}</h3>
      <p class="params-section-desc">{{ $t('settings.updateCheckDesc') }}</p>
      <!-- The whole row toggles the switch, keeping the touch target at 44px. -->
      <label
        class="params-update-row"
        :class="{ 'params-update-row--disabled': updateToggleDisabled }"
      >
        <span class="params-update-label">{{ $t('settings.updateCheckLabel') }}</span>
        <MkToggle
          :model-value="!!updateStatus?.enabled"
          :disabled="updateToggleDisabled"
          :aria-label="$t('settings.updateCheckLabel')"
          @update:model-value="onToggleUpdateCheck"
        />
      </label>
      <p v-if="updateStatus?.locked" class="params-update-locked">
        {{ $t('settings.updateCheckLocked') }}
      </p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { setLocale, getLocale, AVAILABLE_LOCALES } from '@/i18n'
import { useUpdateCheck } from '@/composables/useUpdateCheck'
import MkToggle from '@/components/common/MkToggle.vue'

const currentLocale = ref(getLocale())
const { status: updateStatus, load: loadUpdateStatus, setEnabled } = useUpdateCheck()
const savingUpdateCheck = ref(false)
const updateToggleDisabled = computed(
  () => !updateStatus.value || updateStatus.value.locked || savingUpdateCheck.value,
)

async function onLocaleChange(code) {
  const changed = await setLocale(code)
  if (changed) currentLocale.value = code
}

async function onToggleUpdateCheck(enabled) {
  savingUpdateCheck.value = true
  await setEnabled(enabled)
  savingUpdateCheck.value = false
}

onMounted(loadUpdateStatus)
</script>

<style scoped>
.params-lang-select-wrap {
  max-width: 260px;
}
.params-lang-select {
  width: 100%;
  padding: 9px var(--space-3-5);
  border-radius: var(--radius-btn);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  appearance: auto;
}
.params-lang-select:focus {
  outline: none;
  border-color: var(--accent-500);
}
.params-update-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: fit-content;
  min-height: var(--touch-target);
  cursor: pointer;
}
.params-update-row--disabled {
  cursor: not-allowed;
}
.params-update-label {
  font-size: var(--text-sm);
  color: var(--text-primary);
}
.params-update-locked {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
