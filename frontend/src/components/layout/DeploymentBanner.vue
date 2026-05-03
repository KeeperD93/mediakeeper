<template>
  <div v-if="show" class="mk-deployment-banner" role="alert">
    <TriangleAlert :size="18" :stroke-width="2.2" />
    <div class="mk-deployment-banner__body">
      <strong>{{ $t('deploymentBanner.encryptionKey.title') }}</strong>
      <span>{{ $t('deploymentBanner.encryptionKey.text') }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { TriangleAlert } from 'lucide-vue-next'
import { useEncryptionKeyStatus } from '@/composables/useEncryptionKeyStatus'

const { status, refresh } = useEncryptionKeyStatus()

const show = computed(() => status.value?.warning === true)

onMounted(() => { refresh() })
</script>

<style scoped>
.mk-deployment-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  background: var(--mk-danger-bg, #3a0c0c);
  color: var(--mk-danger-fg, #ffd5d5);
  border-bottom: 1px solid var(--mk-danger-border, #6b1f1f);
  font-size: 0.875rem;
  line-height: 1.35;
}
.mk-deployment-banner svg { flex-shrink: 0; }
.mk-deployment-banner__body { display: flex; flex-direction: column; gap: 0.125rem; }
.mk-deployment-banner__body strong { font-weight: 600; }
</style>
