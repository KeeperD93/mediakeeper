<template>
  <main class="pmaint-root">
    <div class="pmaint-card">
      <HardHat :size="96" :stroke-width="1.5" class="pmaint-icon" />
      <h1 class="pmaint-title">{{ $t('portal.maintenance.title') }}</h1>
      <p v-if="loaded" class="pmaint-text">{{ text }}</p>
      <p v-else class="pmaint-text pmaint-text--placeholder">&nbsp;</p>
    </div>
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { HardHat } from 'lucide-vue-next'
import { useMaintenance } from '@/composables/portal/useMaintenance'

const { t } = useI18n()
const { fetchMaintenanceState } = useMaintenance()

const text = ref('')
const loaded = ref(false)

onMounted(async () => {
  const state = await fetchMaintenanceState({ force: true })
  text.value = state?.text || t('portal.maintenance.defaultText')
  loaded.value = true
})
</script>

<style scoped>
.pmaint-root {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  background: var(--bg-primary);
}
.pmaint-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 1.25rem;
  max-width: 540px;
}
.pmaint-icon {
  color: var(--portal-color-warning);
}
.pmaint-title {
  font-size: var(--portal-text-2xl);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  margin: 0;
}
.pmaint-text {
  font-size: var(--portal-text-base);
  color: var(--text-primary);
  line-height: 1.5;
  margin: 0;
  white-space: pre-line;
}
.pmaint-text--placeholder {
  min-height: 1.5em;
}
</style>
