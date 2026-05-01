<template>
  <Teleport to="body">
    <div v-if="profileOpen" class="up-overlay" @click="profileOpen = false" />
    <Transition name="pop-profile">
      <div v-if="profileOpen" class="up-pop" :style="profileStyle">
        <div class="up-header">
          <div class="up-avatar" :style="{ background: avatarColors[0] }">{{ profileName[0]?.toUpperCase() }}</div>
          <div class="up-hinfo">
            <div class="up-name">{{ profileName }}</div>
            <div v-if="userProfile" class="up-sub">{{ userProfile.play_count?.toLocaleString(undefined) }} lectures — {{ ticksToDuration(userProfile.total_ticks) }}</div>
          </div>
          <button class="up-close" @click="profileOpen = false">
            <X :size="14" :stroke-width="2.5" />
          </button>
        </div>
      <div v-if="!userProfile" class="up-loading">
        <div class="skel-line w70" /><div class="skel-line w50 up-skel-spaced" /><div class="skel-line w60 up-skel-spaced" />
      </div>
      <div v-else-if="userProfile._error" class="up-empty up-empty-wide">{{ $t('stats.profileError') }}</div>
      <template v-else>
        <div class="up-body">
          <div class="up-col">
            <div class="up-section">
              <div class="up-stitle">{{ $t('stats.lastPlay') }}</div>
              <div class="up-detail" :title="lastPlayText">{{ lastPlayText }}</div>
              <div class="up-meta" :title="lastMetaText">{{ lastMetaText }}</div>
            </div>
            <div class="up-section">
              <div class="up-stitle">{{ $t('stats.topMoviesUser') }}</div>
              <div v-if="!userProfile.top_movies?.length" class="up-empty">{{ $t('common.none') }}</div>
              <div v-for="(m, i) in userProfile.top_movies" :key="'m' + i" class="up-rank-item" :title="m.name">
                <span class="up-rank-n">{{ i + 1 }}</span>
                <img v-if="m.item_id" :src="'/api/emby/image/' + m.item_id" class="up-rank-thumb" @error="e => e.target.style.display = 'none'" />
                <span class="up-rank-name">{{ m.name }}</span>
                <span class="up-rank-val">{{ m.plays }}</span>
              </div>
            </div>
            <div class="up-section">
              <div class="up-stitle">{{ $t('stats.topSeriesUser') }}</div>
              <div v-if="!userProfile.top_series?.length" class="up-empty">{{ $t('common.none') }}</div>
              <div v-for="(s, i) in userProfile.top_series" :key="'s' + i" class="up-rank-item" :title="s.name">
                <span class="up-rank-n">{{ i + 1 }}</span>
                <span class="up-rank-name">{{ s.name }}</span>
                <span class="up-rank-val">{{ s.plays }}</span>
              </div>
            </div>
          </div>
          <div class="up-col">
            <div class="up-section">
              <div class="up-stitle">{{ $t('stats.flux') }}</div>
              <div v-for="m in userProfile.by_method" :key="m.method" class="up-flux-row" :title="m.method">
                <span class="up-flux-dot" :class="fluxClass(m.method)" />
                <span class="up-flux-name">{{ m.method }}</span>
                <span class="up-flux-val">{{ m.count }}</span>
              </div>
            </div>
            <div v-if="upRadarData.length" class="up-section">
              <div class="up-stitle">{{ $t('stats.genres') }}</div>
              <svg viewBox="0 0 260 260" class="up-radar-svg">
                <polygon v-for="lvl in [1, .75, .5, .25]" :key="'url' + lvl" :points="upRadarGridPts(lvl)" fill="none" stroke="rgba(255,255,255,.08)" stroke-width=".5" />
                <line v-for="(g, i) in upRadarData" :key="'ura' + i" x1="130" y1="130" :x2="upRadarPt(i, 1).x" :y2="upRadarPt(i, 1).y" stroke="rgba(255,255,255,.05)" stroke-width=".5" />
                <polygon :points="upRadarDataPts" fill="rgba(var(--accent-rgb),.25)" stroke="var(--accent-500)" stroke-width="1.5" />
                <g v-for="(g, i) in upRadarData" :key="'urg' + i" class="up-radar-node">
                  <title>{{ g.name }} — {{ g.plays }} {{ $t('stats.plays') }}</title>
                  <circle :cx="upRadarPt(i, g.pct).x" :cy="upRadarPt(i, g.pct).y" r="2" fill="var(--accent-400)" />
                  <text :x="upRadarLabelPt(i).x" :y="upRadarLabelPt(i).y" text-anchor="middle" class="radar-label radar-label-sm">{{ g.name }}</text>
                  <circle :cx="upRadarLabelPt(i).x" :cy="upRadarLabelPt(i).y - 3" r="14" fill="transparent" />
                </g>
              </svg>
            </div>
            <div class="up-section">
              <div class="up-stitle">{{ $t('stats.trend') }}</div>
              <div v-if="userProfile.by_library?.length" class="up-trend-bars">
                <div v-for="lib in userProfile.by_library" :key="lib.name" class="up-trend-row" :title="lib.name">
                  <span class="up-trend-name">{{ lib.name }}</span>
                  <div class="up-trend-track"><div class="up-trend-fill" :style="{ width: Math.round(lib.count / Math.max(1, ...userProfile.by_library.map(l => l.count)) * 100) + '%' }" /></div>
                  <span class="up-trend-val">{{ lib.count }}</span>
                </div>
              </div>
              <div v-else class="up-empty">{{ $t('stats.noData') }}</div>
            </div>
          </div>
        </div>
        <div class="up-section up-section-activity">
          <div class="up-stitle">{{ $t('stats.activity30d') }}</div>
          <div class="up-activity-chart">
            <div v-for="d in userProfile.daily_activity" :key="d.date" class="up-act-bar"
              :style="{ height: upBarH(d.count) + '%' }"
              :title="d.date + ' : ' + d.count + ' lectures'" />
          </div>
        </div>
        </template>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useStatsUI } from '@/composables/useStatsUI'
import { useStats } from '@/composables/useStats'
import { X } from 'lucide-vue-next'

const { profileOpen, profileName, profileStyle, userProfile, avatarColors } = useStatsUI()
const { ticksToDuration, timeAgo } = useStats()

const lastPlayText = computed(() => {
  const p = userProfile.value
  if (!p) return '—'
  return p.last_series ? `${p.last_series} — ${p.last_play || ''}` : (p.last_play || '—')
})
const lastMetaText = computed(() => {
  const p = userProfile.value
  if (!p) return ''
  return `${p.last_device || '—'} — ${p.last_client || '—'} — ${p.last_seen ? timeAgo(p.last_seen) : '—'}`
})

function fluxClass(m) { return m === 'DirectPlay' ? 'up-flux-dot--good' : m === 'Transcode' ? 'up-flux-dot--warn' : 'up-flux-dot--info' }
function upBarH(v) {
  if (!userProfile.value?.daily_activity) return 0
  const mx = Math.max(...userProfile.value.daily_activity.map(d => d.count), 1)
  return Math.round((v / mx) * 100)
}

const upRadarData = computed(() => {
  if (!userProfile.value?.by_genre?.length) return []
  const g = userProfile.value.by_genre
  const mx = Math.max(1, ...g.map(x => x.plays))
  return g.slice(0, 12).map(x => ({ name: x.name, plays: x.plays, pct: x.plays / mx }))
})
function upRadarPt(i, pct) {
  const n = upRadarData.value.length || 1
  const a = (Math.PI * 2 * i) / n - Math.PI / 2
  return { x: 130 + Math.cos(a) * 75 * pct, y: 130 + Math.sin(a) * 75 * pct }
}
function upRadarLabelPt(i) {
  const n = upRadarData.value.length || 1
  const a = (Math.PI * 2 * i) / n - Math.PI / 2
  return { x: 130 + Math.cos(a) * 98, y: 130 + Math.sin(a) * 98 + 3 }
}
function upRadarGridPts(pct) {
  const n = upRadarData.value.length || 1
  return Array.from({ length: n }, (_, i) => upRadarPt(i, pct)).map(p => `${p.x},${p.y}`).join(' ')
}
const upRadarDataPts = computed(() => upRadarData.value.map((g, i) => upRadarPt(i, g.pct)).map(p => `${p.x},${p.y}`).join(' '))
</script>

<style scoped>
.up-overlay { position: fixed; inset: 0; z-index: 9900; background: rgba(0,0,0,0.3); }
.up-pop { position: fixed; z-index: 9901; width: 640px; max-width: calc(100vw - 24px); overflow: hidden; background: rgba(15,20,35,.97); backdrop-filter: blur(24px); border: .5px solid rgba(255,255,255,.1); border-radius: var(--radius-card); padding: 20px; box-shadow: 0 20px 60px rgba(0,0,0,.4); }
.pop-profile-enter-active, .pop-profile-leave-active { transition: all var(--duration-base) ease; }
.pop-profile-enter-from, .pop-profile-leave-to { opacity: 0; transform: translateY(6px); }
.up-header { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
.up-avatar { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: var(--text-base); font-weight: var(--font-bold); color: #fff; flex-shrink: 0; }
.up-hinfo { flex: 1; min-width: 0; }
.up-name { font-size: var(--text-md); font-weight: var(--font-medium); color: var(--text-primary); }
.up-sub { font-size: var(--text-2xs); color: var(--text-muted); margin-top: 2px; }
.up-close { width: 28px; height: 28px; border-radius: var(--radius-btn); background: var(--surface-2); border: .5px solid var(--border-strong); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.up-close:hover { background: rgba(239,68,68,.1); color: var(--color-error); border-color: rgba(239,68,68,.2); }
.up-loading { padding: 20px 0; }
.up-body { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; min-width: 0; }
.up-body > .up-col { min-width: 0; overflow: hidden; }
.up-section { margin-bottom: 12px; }
.up-stitle { font-size: var(--text-3xs); text-transform: uppercase; letter-spacing: .5px; color: rgba(255,255,255,.3); margin-bottom: 8px; }
.up-detail { font-size: var(--text-sm); color: var(--text-primary); font-weight: var(--font-regular); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-meta { font-size: var(--text-2xs); color: var(--text-muted); margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-empty { font-size: var(--text-2xs); color: var(--text-muted); }
.up-flux-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; }
.up-flux-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.up-flux-dot--good { background: var(--color-success); }
.up-flux-dot--warn { background: var(--color-warning); }
.up-flux-dot--info { background: var(--color-info); }
.up-flux-name { font-size: var(--text-2xs); color: rgba(255,255,255,.7); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-flux-val { font-size: var(--text-2xs); font-weight: var(--font-medium); color: rgba(255,255,255,.5); flex-shrink: 0; }
.up-rank-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: .5px solid var(--border-subtle); }
.up-rank-item:last-child { border-bottom: none; }
.up-rank-n { width: 14px; font-size: var(--text-2xs); font-weight: var(--font-medium); color: var(--text-very-faint); text-align: center; flex-shrink: 0; }
.up-rank-thumb { width: 22px; height: 32px; border-radius: 3px; object-fit: cover; flex-shrink: 0; background: var(--surface-2); }
.up-rank-name { flex: 1; font-size: var(--text-xs); color: rgba(255,255,255,.8); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.up-rank-val { font-size: var(--text-2xs); font-weight: var(--font-medium); color: var(--accent-400); flex-shrink: 0; }
.up-activity-chart { display: flex; align-items: flex-end; gap: 2px; height: 60px; padding: 4px 0; }
.up-act-bar { flex: 1; min-width: 0; background: rgba(var(--accent-rgb),.4); border-radius: 2px 2px 0 0; transition: height var(--duration-base); min-height: 1px; }
.up-act-bar:hover { background: rgba(var(--accent-rgb),.7); }
.up-trend-bars { display: flex; flex-direction: column; gap: 4px; }
.up-trend-row { display: flex; align-items: center; gap: 6px; }
.up-trend-name { width: 70px; font-size: var(--text-3xs); color: rgba(255,255,255,.6); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; text-align: right; }
.up-trend-track { flex: 1; height: 8px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
.up-trend-fill { height: 100%; background: linear-gradient(90deg, rgba(var(--accent-rgb),.5), rgba(var(--accent-rgb),.8)); border-radius: 4px; transition: width var(--duration-slow); }
.up-trend-val { width: 24px; font-size: var(--text-3xs); font-weight: var(--font-medium); color: var(--accent-400); text-align: right; flex-shrink: 0; }
.up-radar-svg { width: 100%; max-width: 260px; height: auto; display: block; margin: 0 auto; }
.radar-label { font-size: 8px; fill: rgba(255,255,255,.5); font-weight: var(--font-regular); }
.skel-line { height: 12px; border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,.02) 25%, rgba(255,255,255,.05) 50%, rgba(255,255,255,.02) 75%); background-size: 200% 100%; animation: up-sk var(--duration-animation) ease-in-out infinite; }
.w50 { width: 50%; } .w60 { width: 60%; } .w70 { width: 70%; }
@keyframes up-sk { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.up-skel-spaced { margin-top: 8px; }
.up-empty-wide { padding: 16px 0; }
.radar-label-sm { font-size: 7px; }
.up-section-activity { margin-top: 4px; }
@media (max-width: 767px) {
  /* Mobile — override the dynamic click-based positioning so the popup stays
   * inside the viewport and scrolls internally instead of getting clipped. */
  .up-pop {
    width: calc(100vw - 24px) !important;
    top: 12px !important;
    left: 12px !important;
    right: 12px !important;
    bottom: auto !important;
    transform: none !important;
    max-height: calc(100dvh - 24px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    padding: 16px;
  }
  .up-body { grid-template-columns: 1fr; }
  .up-header {
    position: sticky;
    top: -16px;
    z-index: 1;
    background: rgba(15,20,35,.97);
    margin: -16px -16px 16px;
    padding: 16px;
    border-bottom: .5px solid var(--border-default);
  }
}
</style>
