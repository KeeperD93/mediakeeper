<template>
  <div>
    <div class="section-head">
      <h2 class="section-title">{{ $t('stats.libraries') }}</h2>
      <button
        v-if="libraries.length >= 2"
        class="cmp-toggle-btn"
        :class="{ active: compareMode }"
        @click="((compareMode = !compareMode), (compareA = null), (compareB = null))"
      >
        <Copy :size="14" />
        {{ compareMode ? $t('common.cancel') : $t('stats.compare') }}
      </button>
    </div>
    <div v-if="compareMode" class="compare-hint glass-card">
      <span v-if="!compareA">{{ $t('stats.clickFirst') }}</span>
      <span v-else-if="!compareB">{{ $t('stats.clickSecond') }}</span>
    </div>
    <div v-if="compareA && compareB" class="compare-view glass-card">
      <div class="cmp-header">
        <span class="cmp-name">{{ compareA.name }}</span>
        <span class="cmp-vs">VS</span>
        <span class="cmp-name">{{ compareB.name }}</span>
      </div>
      <div v-for="metric in compareMetrics" :key="metric.key" class="cmp-row">
        <span class="cmp-val-l">{{ metric.fmtA }}</span>
        <div class="cmp-bar-wrap">
          <div class="cmp-bar-l" :style="{ width: metric.pctA + '%' }" />
          <span class="cmp-label">{{ metric.label }}</span>
          <div class="cmp-bar-r" :style="{ width: metric.pctB + '%' }" />
        </div>
        <span class="cmp-val-r">{{ metric.fmtB }}</span>
      </div>
    </div>
    <div v-if="loadingLibraries" class="lib-grid">
      <div v-for="n in 4" :key="n" class="glass-card">
        <div class="skel-block skel-block-lib" />
        <div class="lib-skel-body">
          <div class="skel-line w60" />
          <div class="skel-line w40 skel-line-mt6" />
        </div>
      </div>
    </div>
    <div v-else-if="libraries.length" class="lib-grid">
      <div
        v-for="lib in libraries"
        :key="lib.item_id"
        class="glass-card lib-card"
        :class="{
          'lib-selected':
            compareMode && (compareA?.item_id === lib.item_id || compareB?.item_id === lib.item_id),
        }"
        @click="compareMode ? selectCompare(lib) : null"
      >
        <div class="lib-header">
          <img
            v-if="lib.thumb_url"
            :src="lib.thumb_url"
            class="lib-header-img"
            @error="e => (e.target.style.display = 'none')"
          />
          <div class="lib-header-overlay" />
          <span class="lib-header-name">{{ lib.name }}</span>
          <button class="lib-del" @click.stop="deleteLibrary(lib.item_id, lib.name)">
            <X :size="10" :stroke-width="2.5" />
          </button>
        </div>
        <div class="lib-body">
          <div class="lib-row">
            <span class="lib-k">Type</span>
            <span class="lib-v">{{ libTypeName(lib.type) }}</span>
          </div>
          <div v-if="lib.counts?.Movie" class="lib-row">
            <span class="lib-k">{{ $t('stats.movies') }}</span>
            <span class="lib-v">{{ lib.counts.Movie.toLocaleString(undefined) }}</span>
          </div>
          <div v-if="lib.counts?.Series" class="lib-row">
            <span class="lib-k">{{ $t('stats.seriesLabel') }}</span>
            <span class="lib-v">{{ lib.counts.Series.toLocaleString(undefined) }}</span>
          </div>
          <div v-if="lib.counts?.Episode" class="lib-row">
            <span class="lib-k">{{ $t('stats.episodesLabel') }}</span>
            <span class="lib-v">{{ lib.counts.Episode.toLocaleString(undefined) }}</span>
          </div>
          <div class="lib-row">
            <span class="lib-k">{{ $t('stats.size') }}</span>
            <span class="lib-v">{{ fmtSize(lib.size_bytes) }}</span>
          </div>
          <div class="lib-row">
            <span class="lib-k">{{ $t('stats.plays') }}</span>
            <span class="lib-v">{{ (lib.total_plays || 0).toLocaleString(undefined) }}</span>
          </div>
          <div class="lib-row">
            <span class="lib-k">{{ $t('stats.activity') }}</span>
            <span class="lib-v">{{ lib.last_play_at ? timeAgo(lib.last_play_at) : '—' }}</span>
          </div>
        </div>
      </div>
    </div>
    <MkEmptyState v-else :icon="Calendar" size="sm" :title="$t('stats.noLibraries')" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { useApi } from '@/composables/useApi'
import { Calendar, Copy, X } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

const { t } = useI18n()
const { libraries, loadingLibraries, loadLibraries, fmtSize, timeAgo } = useStats()
const { apiDelete } = useApi()

const compareMode = ref(false)
const compareA = ref(null)
const compareB = ref(null)

function selectCompare(lib) {
  if (!compareA.value) {
    compareA.value = lib
    return
  }
  if (compareA.value.item_id === lib.item_id) {
    compareA.value = null
    return
  }
  if (!compareB.value) {
    compareB.value = lib
    return
  }
  if (compareB.value.item_id === lib.item_id) {
    compareB.value = null
    return
  }
  compareA.value = lib
  compareB.value = null
}

const compareMetrics = computed(() => {
  const a = compareA.value,
    b = compareB.value
  if (!a || !b) return []
  const rows = [
    { label: t('stats.files'), key: 'total_items' },
    { label: t('stats.size'), key: 'size_bytes', fmt: fmtSize },
    { label: t('stats.plays'), key: 'total_plays' },
    { label: t('stats.movies'), key: 'movies', fn: l => l.counts?.Movie || 0 },
    { label: t('stats.seriesLabel'), key: 'series', fn: l => l.counts?.Series || 0 },
    { label: t('stats.episodesLabel'), key: 'episodes', fn: l => l.counts?.Episode || 0 },
  ]
  return rows.map(r => {
    const va = r.fn ? r.fn(a) : a[r.key] || 0
    const vb = r.fn ? r.fn(b) : b[r.key] || 0
    const mx = Math.max(va, vb, 1)
    return {
      label: r.label,
      key: r.key,
      fmtA: r.fmt ? r.fmt(va) : va.toLocaleString(undefined),
      fmtB: r.fmt ? r.fmt(vb) : vb.toLocaleString(undefined),
      pctA: Math.round((va / mx) * 100),
      pctB: Math.round((vb / mx) * 100),
    }
  })
})

const libTypeNames = computed(() => ({
  movies: t('stats.movies'),
  tvshows: t('stats.seriesLabel'),
  music: t('stats.music'),
  mixed: t('stats.mixed'),
}))
function libTypeName(tp) {
  return libTypeNames.value[tp] || tp || t('stats.other')
}

async function deleteLibrary(id, nm) {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('stats.deleteLibConfirm', { name: nm }),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  try {
    await apiDelete(`/api/stats/libraries/${encodeURIComponent(id)}`)
    loadLibraries()
  } catch (e) {
    console.error('[StatsLibrariesSection.deleteLibrary] failed to delete library', e)
  }
}
</script>

<style scoped>
.section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  margin-top: 28px;
}
.section-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.skel-block {
  border-radius: var(--radius-card);
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.02) 25%,
    rgb(255, 255, 255, 0.05) 50%,
    rgb(255, 255, 255, 0.02) 75%
  );
  background-size: 200% 100%;
  animation: lib-sk var(--duration-animation) ease-in-out infinite;
}
.skel-line {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.02) 25%,
    rgb(255, 255, 255, 0.05) 50%,
    rgb(255, 255, 255, 0.02) 75%
  );
  background-size: 200% 100%;
  animation: lib-sk var(--duration-animation) ease-in-out infinite;
}
.w40 {
  width: 40%;
}
.w60 {
  width: 60%;
}
@keyframes lib-sk {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
.skel-block-lib {
  height: 80px;
}
.lib-skel-body {
  padding: 10px;
}
.skel-line-mt6 {
  margin-top: 6px;
}

.lib-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.lib-card {
  overflow: hidden;
  cursor: default;
}
.lib-header {
  position: relative;
  height: 80px;
  overflow: hidden;
  background: linear-gradient(135deg, rgb(var(--accent-rgb), 0.15), rgb(139, 92, 246, 0.1));
}
.lib-header-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.lib-header-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgb(var(--bg-primary-rgb), 0.85) 5%, transparent 60%);
}
.lib-header-name {
  position: absolute;
  bottom: 8px;
  left: 12px;
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  text-shadow: 0 1px 4px rgb(0, 0, 0, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.lib-del {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0, 0, 0, 0.5);
  border: 0.5px solid rgb(239, 68, 68, 0.3);
  color: #ef4444;
  cursor: pointer;
  opacity: 0;
  transition: all var(--duration-fast);
}
@media (hover: hover) {
  .lib-card:hover .lib-del {
    opacity: 1;
  }
}
@media (hover: none) {
  .lib-del {
    opacity: 1;
  }
}
.lib-del:hover {
  background: #ef4444;
  color: var(--text-primary);
}
.lib-body {
  padding: 6px 12px 10px;
}
.lib-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  border-bottom: 0.5px solid var(--border-subtle);
}
.lib-row:last-child {
  border-bottom: none;
}
.lib-k {
  font-size: var(--text-2xs);
  color: #22d3ee;
}
.lib-v {
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.7);
  font-weight: var(--font-regular);
  text-align: right;
  max-width: 55%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cmp-toggle-btn {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 5px 14px;
  border-radius: var(--radius-pill);
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .cmp-toggle-btn:hover:not(.active) {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
  .cmp-toggle-btn.active:hover {
    border-color: #ef4444;
    transform: translateY(-1px);
  }
}
.cmp-toggle-btn.active {
  background: rgb(239, 68, 68, 0.08);
  border-color: rgb(239, 68, 68, 0.35);
  color: var(--color-error);
}
.compare-hint {
  padding: 10px 16px;
  margin-bottom: 12px;
  font-size: var(--text-xs);
  color: var(--accent-400);
  text-align: center;
}
.lib-selected {
  border-color: var(--accent-500);
  box-shadow:
    0 0 0 1px var(--accent-500),
    0 0 20px rgb(var(--accent-rgb), 0.1);
}
.compare-view {
  padding: 16px 20px;
  margin-bottom: 14px;
}
.cmp-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}
.cmp-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  flex: 1;
  text-align: center;
}
.cmp-vs {
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  color: var(--accent-400);
  text-transform: uppercase;
  letter-spacing: 1px;
  flex-shrink: 0;
}
.cmp-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
}
.cmp-val-l,
.cmp-val-r {
  width: 60px;
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: rgb(255, 255, 255, 0.6);
}
.cmp-val-l {
  text-align: right;
}
.cmp-val-r {
  text-align: left;
}
.cmp-bar-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0;
  height: 18px;
  position: relative;
}
.cmp-bar-l {
  height: 10px;
  background: var(--accent-500);
  border-radius: 3px 0 0 3px;
  margin-left: auto;
  min-width: 2px;
  transition: width var(--duration-slow);
}
.cmp-label {
  font-size: 0.58rem;
  color: var(--text-muted);
  padding: 0 6px;
  white-space: nowrap;
  flex-shrink: 0;
  text-align: center;
  min-width: 60px;
}
.cmp-bar-r {
  height: 10px;
  background: #06b6d4;
  border-radius: 0 3px 3px 0;
  min-width: 2px;
  transition: width var(--duration-slow);
}

@media (max-width: 768px) {
  .cmp-val-l,
  .cmp-val-r {
    width: 40px;
    font-size: var(--text-2xs);
  }
}
</style>
