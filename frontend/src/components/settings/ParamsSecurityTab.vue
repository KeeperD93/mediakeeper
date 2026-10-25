<template>
  <div class="params-security">
    <SecurityPasswordForm />

    <SecurityBlocksSection
      :blocks="blocks"
      :loading="loadingBlocks"
      :display-ip="displayIp"
      :format-date="formatDate"
      @add="modalOpen = true"
      @unblock="removeBlock"
    />

    <SecurityAttemptsSection
      v-model:only-failures="onlyFailures"
      :attempts="attempts"
      :loading="loadingAttempts"
      :display-ip="displayIp"
      :format-date="formatDate"
      @filter-change="loadAttempts"
      @block-ip="quickBlockIp"
    />

    <SecurityBlockModal v-if="modalOpen" @close="modalOpen = false" @submit="submitBlock" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useParamsSecurity } from '@/composables/useParamsSecurity'
import SecurityPasswordForm from './security/SecurityPasswordForm.vue'
import SecurityBlocksSection from './security/SecurityBlocksSection.vue'
import SecurityAttemptsSection from './security/SecurityAttemptsSection.vue'
import SecurityBlockModal from './security/SecurityBlockModal.vue'
import '@/assets/styles/settings/params-security.css'

const {
  blocks,
  attempts,
  loadingBlocks,
  loadingAttempts,
  onlyFailures,
  displayIp,
  formatDate,
  loadBlocks,
  loadAttempts,
  addBlock,
  removeBlock,
  quickBlockIp,
} = useParamsSecurity()

const modalOpen = ref(false)

async function submitBlock(payload) {
  await addBlock(payload)
  modalOpen.value = false
  await loadBlocks()
}

onMounted(async () => {
  await Promise.all([loadBlocks(), loadAttempts()])
})
</script>

<style scoped>
.params-security {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
</style>
