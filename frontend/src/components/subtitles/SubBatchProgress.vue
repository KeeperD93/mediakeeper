<template>
  <div class="sub-batch-progress glass-card">
    <div class="sub-batch-header">
      <span class="sub-batch-title">{{ $t('subtitles.batchProgress') }}</span>
      <button class="sub-batch-cancel-btn" @click="$emit('cancel')">{{ $t('common.cancel') }}</button>
    </div>
    <div class="sub-batch-bar-wrap">
      <div class="sub-batch-bar">
        <div class="sub-batch-fill" :style="{ width: pct + '%' }" />
      </div>
      <span class="sub-batch-pct">{{ progress.current }}/{{ progress.total }}</span>
    </div>
    <div v-if="progress.label" class="sub-batch-label">{{ progress.label }}</div>
    <div v-if="progress.completed && progress.completed.length" class="sub-batch-stat stat-ok">
      {{ progress.completed.length }} {{ $t('subtitles.downloaded').toLowerCase() }}
    </div>
    <div v-if="progress.failed && progress.failed.length" class="sub-batch-stat stat-err">
      {{ progress.failed.length }} {{ $t('common.error').toLowerCase() }}
    </div>
    <div v-if="!progress.running && progress.total > 0" class="sub-batch-done">
      {{ $t('subtitles.batchComplete') }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'

const emit = defineEmits(['cancel'])
const { apiGet } = useApi()

const progress = ref({ running: false, current: 0, total: 0, label: '', completed: [], failed: [], skipped: [] })
let _timer = null

const pct = computed(() => {
  if (!progress.value.total) return 0
  return Math.round((progress.value.current / progress.value.total) * 100)
})

async function poll() {
  try {
    const d = await apiGet('/api/subtitles/batch-progress')
    if (d) progress.value = d
    if (!d.running) {
      clearInterval(_timer)
    }
  } catch { /* silent: progress poll, retries next tick */ }
}

onMounted(() => {
  poll()
  _timer = setInterval(poll, 2000)
})

onUnmounted(() => {
  clearInterval(_timer)
})
</script>

<style scoped>
.sub-batch-progress { padding: 12px 14px; margin-bottom: 8px; }
.sub-batch-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.sub-batch-title { font-size: var(--text-xs); font-weight: var(--font-medium); color: var(--text-primary); }
.sub-batch-cancel-btn {
  padding: 4px 10px; border-radius: var(--radius-btn); font-size: var(--text-2xs);
  background: rgba(244,63,94,.1); color: #fb7185; border: .5px solid rgba(244,63,94,.2);
  cursor: pointer; font-family: inherit;
}
.sub-batch-cancel-btn:hover { background: rgba(244,63,94,.2); }

.sub-batch-bar-wrap { display: flex; align-items: center; gap: 8px; }
.sub-batch-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.sub-batch-fill { height: 100%; border-radius: 3px; background: var(--accent-500); transition: width var(--duration-slow); }
.sub-batch-pct { font-size: var(--text-3xs); color: var(--text-muted); min-width: 36px; text-align: right; }

.sub-batch-label { font-size: var(--text-2xs); color: var(--text-muted); margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub-batch-stat { font-size: var(--text-3xs); margin-top: 4px; }
.stat-ok { color: var(--color-success); }
.stat-err { color: #f43f5e; }
.sub-batch-done { font-size: var(--text-2xs); font-weight: var(--font-medium); color: var(--accent-400); margin-top: 8px; }

.glass-card { background: var(--surface-1); backdrop-filter: blur(16px); border: .5px solid var(--border-default); border-radius: var(--radius-card); }
</style>
