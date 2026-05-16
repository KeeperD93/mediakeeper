<template>
  <div>
    <div v-if="!ignored.length" class="wlig-empty">
      <p>{{ $t('watchlist.noIgnored') }}</p>
    </div>
    <template v-else>
      <div class="wlig-header">
        <p class="wlig-count">
          {{ $t('watchlist.ignoredEpisodesCount', { count: ignored.length }) }}
        </p>
        <button class="wlig-restore-all" @click="restoreAll">
          {{ $t('watchlist.restoreAll') }}
        </button>
      </div>
      <div class="wlig-list">
        <div v-for="(group, tid) in grouped" :key="tid" class="wlig-row glass-row">
          <div class="wlig-row-name" :title="group.name">{{ group.name }}</div>
          <div class="wlig-tags">
            <span v-for="ep in group.eps" :key="ep.key" class="wlig-tag">
              S{{ pad(ep.season) }}E{{ pad(ep.episode) }}
              <button
                class="wlig-tag-x"
                :title="$t('common.restore')"
                @click="restoreKeys([ep.key])"
              >
                ✕
              </button>
            </span>
          </div>
          <button class="wlig-restore-row" @click="restoreKeys(group.keys)">
            {{ $t('common.restore') }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { computed } from 'vue'
import { useWatchlist } from '@/composables/useWatchlist'
import { useConfirm } from '@/composables/useConfirm'
const { data, ignored, restoreKeys } = useWatchlist()
const mkConfirm = useConfirm()

function pad(n) {
  return String(n).padStart(2, '0')
}

const grouped = computed(() => {
  const map = {}
  for (const k of ignored.value) {
    const m = k.match(/^(\d+)_s(\d+)_e(\d+)$/)
    if (!m) continue
    const [, tid, s, e] = m
    if (!map[tid]) {
      const series = data.value?.series?.find(x => String(x.tmdb_id) === tid)
      map[tid] = { name: series?.name || `TMDB #${tid}`, eps: [], keys: [] }
    }
    map[tid].eps.push({ season: +s, episode: +e, key: k })
    map[tid].keys.push(k)
  }
  for (const g of Object.values(map)) {
    g.eps.sort((a, b) => a.season - b.season || a.episode - b.episode)
  }
  return map
})

async function restoreAll() {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.restore'),
    message: t('watchlist.restoreConfirm', { n: ignored.value.length }),
    variant: 'warn',
  })
  if (!ok) return
  restoreKeys([...ignored.value])
}
</script>

<style scoped>
.wlig-empty {
  text-align: center;
  padding: 64px 24px;
  color: var(--text-muted);
  font-size: var(--text-base);
}
.wlig-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.wlig-count {
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.wlig-restore-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 5px 14px;
  border-radius: var(--radius-btn);
  background: rgb(255, 255, 255, 0.03);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  font-family: inherit;
}
@media (hover: hover) {
  .wlig-restore-all:hover {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}

.wlig-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.glass-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  background: var(--surface-1);
  backdrop-filter: blur(8px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-btn);
  transition: border-color var(--duration-fast);
}
.glass-row:hover {
  border-color: rgb(99, 102, 241, 0.2);
}
.wlig-row-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  width: 200px;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wlig-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  flex: 1;
  min-width: 0;
}
.wlig-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--text-3xs);
  font-family: 'SF Mono', monospace;
  padding: 2px 7px;
  border-radius: 5px;
  background: var(--surface-2);
  color: var(--text-secondary);
  border: 0.5px solid rgb(255, 255, 255, 0.07);
}
.wlig-tag-x {
  background: none;
  border: none;
  color: rgb(156, 163, 175, 0.5);
  cursor: pointer;
  font-size: 0.55rem;
  padding: 0;
  transition: color 0.1s;
  line-height: var(--lh-tight);
}
.wlig-tag-x:hover {
  color: var(--color-error);
}
.wlig-restore-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 4px 12px;
  border-radius: var(--radius-btn);
  background: rgb(255, 255, 255, 0.03);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  font-family: inherit;
  flex-shrink: 0;
}
@media (hover: hover) {
  .wlig-restore-row:hover {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}

/* Mobile: stack the row vertically so tags don't get squeezed into the restore button */
@media (max-width: 767px) {
  .glass-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 10px 12px;
  }
  .wlig-row-name {
    width: auto;
    flex: none;
  }
  .wlig-tags {
    width: 100%;
    gap: 5px;
    flex: none;
  }
  .wlig-tag {
    font-size: var(--text-2xs);
    padding: 3px 8px;
    min-height: 26px;
  }
  .wlig-tag-x {
    font-size: var(--text-2xs);
    min-width: 18px;
    min-height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .wlig-restore-row {
    align-self: flex-end;
    min-height: 32px;
    padding: 6px 12px;
    font-size: var(--text-2xs);
  }
}
</style>
