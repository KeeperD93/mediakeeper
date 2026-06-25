<template>
  <div class="doub-kpis">
    <div class="doub-kpi glass-kpi">
      <span class="kpi-val doub-kpi-err">{{ activeCount }}</span>
      <span class="kpi-label">{{ $t('duplicates.activeDuplicates') }}</span>
    </div>
    <div class="doub-kpi glass-kpi">
      <span class="kpi-val doub-kpi-warn">{{ reclaimable }}</span>
      <span class="kpi-label">{{ $t('duplicates.reclaimableSpace') }}</span>
    </div>
    <div class="doub-kpi glass-kpi">
      <span class="kpi-val doub-kpi-ok">{{ deletedCount }}</span>
      <span class="kpi-label">{{ $t('duplicates.cleanedFiles') }}</span>
    </div>
    <div class="doub-kpi glass-kpi">
      <span class="kpi-val doub-kpi-info">{{ formatBytes(freedBytes) }}</span>
      <span class="kpi-label">{{ $t('duplicates.totalFreedSpace') }}</span>
    </div>
  </div>
</template>

<script setup>
import { formatBytes } from '@/utils/duplicates'

defineProps({
  activeCount: { type: Number, default: 0 },
  reclaimable: { type: String, default: '0 Mo' },
  deletedCount: { type: Number, default: 0 },
  freedBytes: { type: Number, default: 0 },
})
</script>
