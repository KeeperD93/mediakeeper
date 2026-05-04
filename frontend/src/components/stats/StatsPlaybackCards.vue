<template>
  <div>
    <div class="section-head">
      <h2 class="section-title">{{ $t('stats.playbackStats') }}</h2>
      <div class="period-pills">
        <button
          v-for="d in periodOptions"
          :key="d"
          class="pill"
          :class="{ active: playbackDays === d }"
          @click="changePlaybackDays(d)"
        >
          {{ d }}j
        </button>
        <button class="pill" :class="{ active: playbackDays === 0 }" @click="changePlaybackDays(0)">
          {{ $t('common.all') }}
        </button>
        <button
          class="pill pill-customize"
          :class="{ active: customizeMode }"
          @click="customizeMode = !customizeMode"
        >
          <SlidersHorizontal :size="11" />
          {{ customizeMode ? $t('dashboard.done') : $t('dashboard.customize') }}
        </button>
      </div>
    </div>
    <div v-if="!playback && loadingPlayback" class="top-grid">
      <div v-for="n in 9" :key="n" class="glass-card top-card-skel">
        <div class="skel-line w50 skel-line-mb12" />
        <div class="skel-line w70" />
        <div class="skel-line w40" />
      </div>
    </div>
    <div v-show="playback" class="top-grid" :class="{ 'flip-anim': playbackFlip }">
      <div
        v-for="(card, ci) in orderedCards"
        :key="card.id"
        class="glass-card top-card"
        :class="{ 'drag-over': dragOverIdx === ci, dragging: customizeMode && dragIdx === ci }"
        :draggable="customizeMode"
        @dragstart="onDragStart(ci, $event)"
        @dragover.prevent="onDragOver(ci)"
        @dragend="onDragEnd"
        @drop.prevent="onDrop(ci)"
      >
        <div v-if="customizeMode" class="drag-handle">
          <GripVertical :size="12" fill="currentColor" />
        </div>
        <template v-if="card.type === 'donut'">
          <div class="top-head">
            <span class="top-title">{{ $t('stats.differentFlux') }}</span>
          </div>
          <div v-if="!playback?.by_method?.length" class="top-empty">{{ $t('stats.noData') }}</div>
          <div v-else class="donut-wrap">
            <svg class="donut-svg" viewBox="0 0 120 120">
              <circle
                v-for="(seg, i) in donutSegments"
                :key="i"
                cx="60"
                cy="60"
                r="48"
                fill="none"
                stroke-width="14"
                :stroke-dasharray="seg.dash"
                :stroke-dashoffset="seg.offset"
                stroke-linecap="round"
                class="donut-seg"
                :style="{ animationDelay: i * 150 + 'ms', stroke: seg.color }"
              />
              <text x="60" y="56" text-anchor="middle" class="donut-total">{{ fluxTotal }}</text>
              <text x="60" y="70" text-anchor="middle" class="donut-sub">
                {{ $t('stats.plays_unit') }}
              </text>
            </svg>
            <div class="donut-legend">
              <div v-for="it in playback?.by_method || []" :key="it.method" class="donut-leg">
                <span class="donut-dot" :style="{ background: fluxColor(it.method) }" />
                <span class="donut-name">{{ it.method }}</span>
                <span class="donut-pct">{{ fluxPct(it.count) }}%</span>
              </div>
            </div>
          </div>
        </template>
        <template v-else-if="card.type === 'genre'">
          <div class="top-head">
            <span class="top-title">{{ $t('stats.topByGenre') }}</span>
            <span class="top-unit">{{ $t('stats.plays_unit') }}</span>
          </div>
          <div v-if="!genreRadarData.length" class="top-empty">{{ $t('stats.noData') }}</div>
          <div v-else class="radar-wrap">
            <svg :viewBox="'0 0 ' + radarSize + ' ' + radarSize" class="radar-svg">
              <polygon
                v-for="lvl in [1, 0.75, 0.5, 0.25]"
                :key="'rl' + lvl"
                :points="radarGridPoints(lvl)"
                fill="none"
                stroke="rgba(255,255,255,.08)"
                stroke-width=".5"
              />
              <line
                v-for="(g, i) in genreRadarData"
                :key="'ra' + i"
                :x1="radarCx"
                :y1="radarCy"
                :x2="radarPt(i, 1).x"
                :y2="radarPt(i, 1).y"
                stroke="rgba(255,255,255,.05)"
                stroke-width=".5"
              />
              <polygon
                :points="radarDataPoints"
                fill="rgba(var(--accent-rgb),.2)"
                stroke="var(--accent-500)"
                stroke-width="1.5"
              />
              <circle
                v-for="(g, i) in genreRadarData"
                :key="'rd' + i"
                :cx="radarPt(i, g.pct).x"
                :cy="radarPt(i, g.pct).y"
                r="2.5"
                fill="var(--accent-400)"
              />
              <text
                v-for="(g, i) in genreRadarData"
                :key="'rt' + i"
                :x="radarLabelPt(i).x"
                :y="radarLabelPt(i).y"
                text-anchor="middle"
                class="radar-label"
              >
                <title v-if="g.name.length > 14">{{ g.name }}</title>
                {{ g.name.length > 14 ? g.name.slice(0, 12) + '…' : g.name }}
              </text>
            </svg>
          </div>
        </template>
        <template v-else>
          <div class="top-head">
            <span class="top-title">{{ card.title }}</span>
            <span class="top-unit">{{ card.unit }}</span>
          </div>
          <div v-if="!card.items?.length" class="top-empty">{{ $t('stats.noData') }}</div>
          <div v-for="(it, i) in card.items" :key="i" class="top-item">
            <span class="top-rank">{{ i + 1 }}</span>
            <img
              v-if="card.imgKey && it[card.imgKey]"
              :src="'/api/emby/image/' + it[card.imgKey]"
              class="top-thumb"
              @error="e => (e.target.style.display = 'none')"
              @mouseenter="showPreview($event, it, card.imgKey)"
              @mouseleave="hidePreview"
              @click="goToActivitySearch(it.name)"
            />
            <div
              v-if="card.avatar"
              class="top-avatar"
              :style="{ background: avatarColors[i % avatarColors.length] }"
            >
              {{ (it.name || '?')[0].toUpperCase() }}
            </div>
            <span
              class="top-name"
              :class="{ 'top-name-clickable': card.avatar && it.user_id }"
              @click="
                card.avatar && it.user_id ? openUserProfile(it.user_id, it.name, $event) : null
              "
            >
              {{ it.name }}
            </span>
            <span class="top-val">{{ card.valFn ? card.valFn(it) : it[card.valKey] }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { GripVertical, SlidersHorizontal } from 'lucide-vue-next'
import { useStatsUI } from '@/composables/useStatsUI'

const { t } = useI18n()
const { playback, loadingPlayback, loadPlayback, resolveSeriesImageId, ticksToHours } = useStats()
const { avatarColors, showPreview, hidePreview, openUserProfile, goToActivitySearch } = useStatsUI()

const periodOptions = [7, 30, 90, 180, 365]
const playbackDays = ref(365)
const playbackFlip = ref(false)

function changePlaybackDays(d) {
  playbackFlip.value = true
  playbackDays.value = d
  loadPlaybackAndResolve(d)
  setTimeout(() => {
    playbackFlip.value = false
  }, 400)
}
async function loadPlaybackAndResolve(days) {
  await loadPlayback(days)
  if (!playback.value) return
  for (const k of ['top_series', 'popular_series'])
    for (const it of playback.value[k] || [])
      if (it.name && !it.series_id) it.series_id = await resolveSeriesImageId(it.name)
}
// Initial load triggered from parent GeneralTab
defineExpose({ loadPlaybackAndResolve })

const rankCards = computed(() => {
  if (!playback.value) return []
  const cards = []
  cards.push({
    id: 'top_movies',
    type: 'rank',
    title: t('stats.topMovies'),
    unit: t('common.plays'),
    items: playback.value.top_movies,
    valKey: 'plays',
    imgKey: 'item_id',
  })
  cards.push({
    id: 'popular_movies',
    type: 'rank',
    title: t('stats.popularMovies'),
    unit: t('stats.users'),
    items: playback.value.popular_movies,
    valKey: 'users',
    imgKey: 'item_id',
  })
  cards.push({
    id: 'top_series',
    type: 'rank',
    title: t('stats.topSeries'),
    unit: t('common.plays'),
    items: playback.value.top_series,
    valKey: 'plays',
    imgKey: 'series_id',
  })
  cards.push({
    id: 'popular_series',
    type: 'rank',
    title: t('stats.popularSeries'),
    unit: t('stats.users'),
    items: playback.value.popular_series,
    valKey: 'users',
    imgKey: 'series_id',
  })
  cards.push({
    id: 'top_watchers',
    type: 'rank',
    title: t('stats.topWatchers'),
    unit: t('common.hours'),
    items: playback.value.top_users_hours,
    valFn: it => ticksToHours(it.ticks),
    avatar: true,
  })
  cards.push({
    id: 'active_users',
    type: 'rank',
    title: t('stats.activeUsersCard'),
    unit: t('common.plays'),
    items: playback.value.top_users,
    valKey: 'plays',
    avatar: true,
  })
  cards.push({ id: 'donut', type: 'donut' })
  if (playback.value.top_transcode_users?.length)
    cards.push({
      id: 'top_transcode',
      type: 'rank',
      title: t('stats.topTranscode'),
      unit: t('common.plays'),
      items: playback.value.top_transcode_users,
      valKey: 'plays',
      avatar: true,
    })
  cards.push({
    id: 'libraries',
    type: 'rank',
    title: t('stats.libraries'),
    unit: t('common.plays'),
    items: playback.value.by_library,
    valKey: 'plays',
  })
  cards.push({ id: 'genre', type: 'genre' })
  if (playback.value.by_audio_language?.length)
    cards.push({
      id: 'audio_lang',
      type: 'rank',
      title: t('stats.audioLanguages'),
      unit: t('common.plays'),
      items: playback.value.by_audio_language,
      valKey: 'plays',
    })
  cards.push({
    id: 'clients',
    type: 'rank',
    title: t('stats.clients'),
    unit: t('common.plays'),
    items: playback.value.by_client,
    valKey: 'plays',
  })
  return cards
})

const customizeMode = ref(false)
const cardOrder = ref(null)
const dragIdx = ref(-1)
const dragOverIdx = ref(-1)
const orderedCards = computed(() => {
  const cards = rankCards.value
  if (!cards.length) return cards
  if (!cardOrder.value) return cards
  const order = cardOrder.value
  const ordered = []
  for (const id of order) {
    const c = cards.find(x => x.id === id)
    if (c) ordered.push(c)
  }
  for (const c of cards) if (!ordered.includes(c)) ordered.push(c)
  return ordered
})
watch(rankCards, cards => {
  if (!cardOrder.value && cards.length) cardOrder.value = cards.map(c => c.id)
})

function onDragStart(i, e) {
  dragIdx.value = i
  e.dataTransfer.effectAllowed = 'move'
}
function onDragOver(i) {
  dragOverIdx.value = i
}
function onDragEnd() {
  dragIdx.value = -1
  dragOverIdx.value = -1
}
function onDrop(toIdx) {
  const fromIdx = dragIdx.value
  if (fromIdx < 0 || fromIdx === toIdx) return
  const cards = orderedCards.value.map(c => c.id)
  const [moved] = cards.splice(fromIdx, 1)
  cards.splice(toIdx, 0, moved)
  cardOrder.value = cards
  dragIdx.value = -1
  dragOverIdx.value = -1
}

const CIRC = 2 * Math.PI * 48
function fluxColor(m) {
  return m === 'DirectPlay'
    ? 'var(--color-success)'
    : m === 'Transcode'
      ? 'var(--color-warning)'
      : 'var(--color-info)'
}
const fluxTotal = computed(() => (playback.value?.by_method || []).reduce((s, x) => s + x.count, 0))
function fluxPct(c) {
  const tot = fluxTotal.value
  return tot > 0 ? ((c / tot) * 100).toFixed(1) : '0'
}
const donutSegments = computed(() => {
  const m = playback.value?.by_method || []
  const tot = fluxTotal.value || 1
  const segs = []
  let off = CIRC * 0.25
  for (const x of m) {
    const pct = x.count / tot
    const dash = pct * CIRC
    segs.push({ color: fluxColor(x.method), dash: `${dash} ${CIRC - dash}`, offset: -off })
    off += dash
  }
  return segs
})

const radarSize = 360,
  radarCx = 180,
  radarCy = 180,
  radarR = 115
const genreRadarData = computed(() => {
  const g = playback.value?.by_genre || []
  if (!g.length) return []
  const mx = Math.max(1, ...g.map(x => x.plays))
  return g.slice(0, 12).map(x => ({ name: x.name, plays: x.plays, pct: x.plays / mx }))
})
function radarPt(i, pct) {
  const n = genreRadarData.value.length || 1,
    a = (Math.PI * 2 * i) / n - Math.PI / 2
  return { x: radarCx + Math.cos(a) * radarR * pct, y: radarCy + Math.sin(a) * radarR * pct }
}
function radarLabelPt(i) {
  const n = genreRadarData.value.length || 1,
    a = (Math.PI * 2 * i) / n - Math.PI / 2,
    r = radarR + 28
  return { x: radarCx + Math.cos(a) * r, y: radarCy + Math.sin(a) * r + 3 }
}
function radarGridPoints(pct) {
  const n = genreRadarData.value.length || 1
  return Array.from({ length: n }, (_, i) => radarPt(i, pct))
    .map(p => `${p.x},${p.y}`)
    .join(' ')
}
const radarDataPoints = computed(() =>
  genreRadarData.value
    .map((g, i) => radarPt(i, g.pct))
    .map(p => `${p.x},${p.y}`)
    .join(' '),
)
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

.top-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.top-grid.flip-anim {
  animation: pc-flip-grid 0.4s ease;
  transform-style: preserve-3d;
}
@keyframes pc-flip-grid {
  0% {
    transform: none;
    filter: none;
  }
  30% {
    transform: perspective(800px) rotateX(4deg);
    filter: blur(2px) brightness(0.7);
  }
  60% {
    transform: perspective(800px) rotateX(-3deg);
    filter: blur(1px) brightness(0.9);
  }
  100% {
    transform: none;
    filter: none;
  }
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: var(--blur-md);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.top-card {
  padding: 14px 16px;
}
.top-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.top-title {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: rgb(255, 255, 255, 0.7);
}
.top-unit {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  color: rgb(255, 255, 255, 0.3);
}
.top-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: 6px 0;
}
.top-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 0.5px solid var(--border-subtle);
}
.top-item:last-child {
  border-bottom: none;
}
.top-rank {
  width: 16px;
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-very-faint);
  text-align: center;
  flex-shrink: 0;
}
.top-thumb {
  width: 24px;
  height: 34px;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
  background: rgb(255, 255, 255, 0.05);
  cursor: pointer;
}
.top-name {
  flex: 1;
  font-size: var(--text-xs);
  color: rgb(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.top-name-clickable {
  cursor: pointer;
}
.top-name-clickable:hover {
  color: var(--accent-400);
  text-decoration: underline;
}
.top-val {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--accent-400);
  flex-shrink: 0;
}
.top-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.55rem;
  font-weight: var(--font-bold);
  color: #fff;
  flex-shrink: 0;
}

.donut-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}
.donut-svg {
  width: 100px;
  height: 100px;
  flex-shrink: 0;
}
.donut-seg {
  animation: pc-donut-in 0.6s ease-out both;
}
@keyframes pc-donut-in {
  from {
    stroke-dasharray: 0 301.6;
  }
}
.donut-total {
  font-size: var(--text-md);
  font-weight: var(--font-medium);
  fill: var(--text-primary);
}
.donut-sub {
  font-size: 9px;
  fill: rgb(255, 255, 255, 0.35);
}
.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.donut-leg {
  display: flex;
  align-items: center;
  gap: 6px;
}
.donut-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.donut-name {
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.7);
  flex: 1;
}
.donut-pct {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: rgb(255, 255, 255, 0.5);
}

.radar-wrap {
  display: flex;
  justify-content: center;
  padding: 4px 0;
}
.radar-svg {
  width: 100%;
  max-width: 340px;
  height: auto;
}
.radar-label {
  font-size: 8px;
  fill: rgb(255, 255, 255, 0.5);
  font-weight: var(--font-regular);
}

.pill-customize {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px 0 4px;
  color: rgb(255, 255, 255, 0.2);
  cursor: grab;
}
.drag-handle:active {
  cursor: grabbing;
}
.dragging {
  opacity: 0.5;
  border: 1px dashed rgb(var(--accent-rgb), 0.4) !important;
}
.drag-over {
  border-color: var(--accent-500) !important;
  box-shadow:
    0 0 0 1px var(--accent-500),
    0 0 16px rgb(var(--accent-rgb), 0.15);
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
  animation: pc-sk var(--duration-animation) ease-in-out infinite;
}
.w40 {
  width: 40%;
}
.w50 {
  width: 50%;
}
.w70 {
  width: 70%;
}
@keyframes pc-sk {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
.top-card-skel {
  padding: 14px 16px;
}
.skel-line-mb12 {
  margin-bottom: 12px;
}

@media (max-width: 1280px) {
  .top-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .top-grid {
    grid-template-columns: 1fr;
  }
}
</style>
