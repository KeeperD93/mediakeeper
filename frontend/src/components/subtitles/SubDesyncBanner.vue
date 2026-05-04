<template>
  <div v-if="desync && desync.desynced" class="sub-desync-banner">
    <AlertCircle :size="14" />
    <span>
      {{ $t('subtitles.desyncWarning') }}
      <strong>{{ desync.delta_sec > 0 ? '+' : '' }}{{ desync.delta_sec }}s</strong>
      <span class="sub-desync-detail">
        (SRT: {{ formatDuration(desync.srt_duration_sec) }} / {{ $t('subtitles.source') }}:
        {{ formatDuration(desync.media_duration_sec) }})
      </span>
    </span>
  </div>
  <div v-if="encoding && encoding.converted" class="sub-encoding-banner">
    <Check :size="14" />
    <span>{{ $t('subtitles.encodingFixed') }}: {{ encoding.original_encoding }} → UTF-8</span>
  </div>
</template>

<script setup>
import { AlertCircle, Check } from 'lucide-vue-next'

defineProps({
  desync: { type: Object, default: null },
  encoding: { type: Object, default: null },
})

function formatDuration(sec) {
  if (!sec) return '0:00'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.floor(sec % 60)
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
.sub-desync-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-top: 8px;
  border-radius: var(--radius-btn);
  font-size: var(--text-2xs);
  background: rgb(var(--color-warning-rgb), 0.08);
  border: 0.5px solid rgb(var(--color-warning-rgb), 0.2);
  color: var(--color-warning);
}
.sub-desync-detail {
  font-size: var(--text-3xs);
  color: var(--text-muted);
}
.sub-encoding-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-top: 4px;
  border-radius: var(--radius-btn);
  font-size: var(--text-2xs);
  background: rgb(var(--color-success-rgb), 0.08);
  border: 0.5px solid rgb(var(--color-success-rgb), 0.2);
  color: var(--color-success);
}
</style>
