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
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { setLocale, getLocale, AVAILABLE_LOCALES } from '@/i18n'

const currentLocale = ref(getLocale())

async function onLocaleChange(code) {
  const changed = await setLocale(code)
  if (changed) currentLocale.value = code
}
</script>

<style scoped>
.params-lang-select-wrap {
  max-width: 260px;
}
.params-lang-select {
  width: 100%;
  padding: 9px 14px;
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
</style>
