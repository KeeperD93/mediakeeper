<template>
  <section class="scl-section">
    <header class="scl-section-head">
      <h3 class="scl-section-title">{{ $t('scheduler.cache.title') }}</h3>
      <p class="scl-section-desc">{{ $t('scheduler.cache.desc') }}</p>
    </header>

    <div v-if="schedCachesLoading && !schedCaches.length" class="scl-skel-wrap">
      <div v-for="i in 2" :key="i" class="scl-skel" />
    </div>

    <div v-else-if="!schedCaches.length" class="scl-empty">
      {{ $t('scheduler.cache.empty') }}
    </div>

    <div v-else class="scl-table-wrap" role="table" :aria-label="$t('scheduler.cache.title')">
      <div class="scl-row scl-row--head" role="row">
        <span role="columnheader">{{ $t('scheduler.cache.colName') }}</span>
        <span role="columnheader" class="scl-col-num">{{ $t('scheduler.cache.colHits') }}</span>
        <span role="columnheader" class="scl-col-num">{{ $t('scheduler.cache.colMisses') }}</span>
        <span role="columnheader" class="scl-col-num">{{ $t('scheduler.cache.colKeys') }}</span>
        <span role="columnheader" class="scl-col-num">{{ $t('scheduler.cache.colSize') }}</span>
        <span role="columnheader" class="scl-col-action" aria-hidden="true" />
      </div>

      <div v-for="cache in schedCaches" :key="cache.id" class="scl-row" role="row">
        <span role="cell" class="scl-cell-name">
          <span class="scl-name">{{ cache.name }}</span>
          <span class="scl-name-meta">
            {{ $t('scheduler.cache.ttlValue', { sec: cache.ttl_seconds }) }}
          </span>
        </span>
        <span role="cell" class="scl-col-num">{{ formatInt(cache.hits) }}</span>
        <span role="cell" class="scl-col-num">{{ formatInt(cache.misses) }}</span>
        <span role="cell" class="scl-col-num">
          {{ formatInt(cache.keys) }}
          <span v-if="cache.max_keys" class="scl-keys-cap">/ {{ formatInt(cache.max_keys) }}</span>
        </span>
        <span role="cell" class="scl-col-num">{{ formatBytes(cache.value_bytes) }}</span>
        <span role="cell" class="scl-col-action">
          <button
            class="scl-clear-btn"
            :aria-label="$t('scheduler.cache.clearAria', { name: cache.name })"
            @click="onClear(cache)"
          >
            <Trash2 :size="14" />
            <span>{{ $t('scheduler.cache.clear') }}</span>
          </button>
        </span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { Trash2 } from 'lucide-vue-next'

const props = defineProps({
  schedCaches: { type: Array, required: true },
  schedCachesLoading: { type: Boolean, default: false },
  schedClearCache: { type: Function, required: true },
})

function formatInt(n) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return '—'
  return n.toLocaleString()
}

// 1 KiB granularity is enough for the admin readout — the cache
// holds ~256 small entries at the most, so any value beyond MiB
// means something is off and is worth surfacing in full.
function formatBytes(bytes) {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let n = bytes
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i += 1
  }
  return `${n.toFixed(n >= 100 ? 0 : n >= 10 ? 1 : 2)} ${units[i]}`
}

function onClear(cache) {
  props.schedClearCache(cache)
}
</script>

<style scoped>
.scl-section {
  margin-top: 28px;
}
.scl-section-head {
  margin-bottom: 12px;
}
.scl-section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0 0 4px;
}
.scl-section-desc {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin: 0;
}
.scl-skel-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.scl-skel {
  height: 44px;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  opacity: 0.6;
  animation: scl-skel-pulse 1.4s ease-in-out infinite;
}
@keyframes scl-skel-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}
.scl-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: 14px 12px;
  text-align: center;
  background: var(--bg-secondary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-card);
}
.scl-table-wrap {
  background: var(--bg-secondary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-card);
  overflow: hidden;
}
.scl-row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) repeat(4, minmax(70px, 1fr)) auto;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-top: 0.5px solid var(--border);
  font-size: var(--text-2xs);
  color: var(--text-secondary);
}
.scl-row:first-child {
  border-top: none;
}
.scl-row--head {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: var(--bg-primary);
  border-bottom: 0.5px solid var(--border);
}
.scl-col-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.scl-col-action {
  text-align: right;
}
.scl-cell-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.scl-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.scl-name-meta {
  font-size: var(--text-3xs);
  color: var(--text-muted);
}
.scl-keys-cap {
  color: var(--text-muted);
  margin-left: 2px;
}
.scl-clear-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 11px;
  border-radius: var(--radius-sm);
  background: rgb(var(--color-error-rgb), 0.08);
  border: 0.5px solid rgb(var(--color-error-rgb), 0.2);
  color: var(--color-error);
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  cursor: pointer;
  font-family: inherit;
  transition: background var(--duration-fast);
  min-height: 28px;
}
@media (hover: hover) {
  .scl-clear-btn:hover {
    background: rgb(var(--color-error-rgb), 0.16);
  }
}

@media (max-width: 767px) {
  .scl-row {
    grid-template-columns: 1fr auto;
    gap: 8px 14px;
    padding: 12px 14px;
  }
  .scl-row--head {
    display: none;
  }
  .scl-cell-name {
    grid-column: 1 / -1;
  }
  .scl-col-num {
    text-align: left;
    display: flex;
    align-items: baseline;
    gap: 6px;
  }
  .scl-col-num::before {
    content: attr(data-label);
    font-size: var(--text-3xs);
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.04em;
  }
  .scl-col-action {
    grid-column: 1 / -1;
    text-align: right;
  }
  .scl-clear-btn {
    min-height: 44px;
    padding: 8px 14px;
  }
}
</style>
