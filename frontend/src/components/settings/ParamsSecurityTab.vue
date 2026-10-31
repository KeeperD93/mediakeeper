<template>
  <div class="params-security">
    <SecurityPasswordForm @attempted="refresh()" />

    <SecurityBlocksSection
      :blocks="blocks"
      :loaded="blocksLoaded"
      :failed="blocksFailed"
      :busy="busy"
      :display-ip="displayIp"
      :format-date="formatDate"
      :scope-label="scopeLabel"
      :reason-label="reasonLabel"
      @refresh="refresh()"
      @add="modalOpen = true"
      @unblock="unblock"
    />

    <SecurityAttemptsSection
      v-model:only-failures="onlyFailures"
      :attempts="attempts"
      :loaded="attemptsLoaded"
      :failed="attemptsFailed"
      :busy="busy"
      :display-ip="displayIp"
      :format-date="formatDate"
      :scope-label="scopeLabel"
      @block-ip="blockAttemptIp"
    />

    <SecurityBlockModal
      v-if="modalOpen"
      :busy="busy"
      :scope-label="scopeLabel"
      @close="modalOpen = false"
      @submit="submitBlock"
    />
  </div>
</template>

<script setup>
import { onActivated, onDeactivated, onUnmounted, ref } from 'vue'
import { useParamsSecurity } from '@/composables/useParamsSecurity'
import SecurityPasswordForm from './security/SecurityPasswordForm.vue'
import SecurityBlocksSection from './security/SecurityBlocksSection.vue'
import SecurityAttemptsSection from './security/SecurityAttemptsSection.vue'
import SecurityBlockModal from './security/SecurityBlockModal.vue'
import '@/assets/styles/settings/params-security.css'

const {
  blocks,
  blocksLoaded,
  blocksFailed,
  attempts,
  attemptsLoaded,
  attemptsFailed,
  onlyFailures,
  busy,
  displayIp,
  formatDate,
  scopeLabel,
  reasonLabel,
  refresh,
  startAutoRefresh,
  stopAutoRefresh,
  addBlock,
  unblock,
  blockAttemptIp,
} = useParamsSecurity()

const modalOpen = ref(false)

async function submitBlock(payload) {
  if (await addBlock(payload)) modalOpen.value = false
}

// The tab lives in SettingsView's KeepAlive: onActivated also runs on the first
// mount. The dialog sits on <body>, so it must close when the tab is switched.
onActivated(() => {
  refresh()
  startAutoRefresh()
})
onDeactivated(() => {
  modalOpen.value = false
  stopAutoRefresh()
})
onUnmounted(stopAutoRefresh)
</script>

<style scoped>
.params-security {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
</style>
