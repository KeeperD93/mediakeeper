<template>
  <div class="up-col">
    <div class="up-section">
      <div class="up-stitle">{{ $t('stats.flux') }}</div>
      <div
        v-for="m in userProfile.by_method"
        :key="m.method"
        class="up-flux-row"
        :title="m.method"
      >
        <span class="up-flux-dot" :class="fluxClass(m.method)" />
        <span class="up-flux-name">{{ m.method }}</span>
        <span class="up-flux-val">{{ m.count }}</span>
      </div>
    </div>
    <div v-if="upRadarData.length" class="up-section">
      <div class="up-stitle">{{ $t('stats.genres') }}</div>
      <svg viewBox="0 0 260 260" class="up-radar-svg">
        <polygon
          v-for="lvl in [1, 0.75, 0.5, 0.25]"
          :key="'url' + lvl"
          :points="upRadarGridPts(lvl)"
          fill="none"
          stroke="rgba(255,255,255,.08)"
          stroke-width=".5"
        />
        <line
          v-for="(g, i) in upRadarData"
          :key="'ura' + i"
          x1="130"
          y1="130"
          :x2="upRadarPt(i, 1).x"
          :y2="upRadarPt(i, 1).y"
          stroke="rgba(255,255,255,.05)"
          stroke-width=".5"
        />
        <polygon
          :points="upRadarDataPts"
          fill="rgba(var(--accent-rgb),.25)"
          stroke="var(--accent-500)"
          stroke-width="1.5"
        />
        <g v-for="(g, i) in upRadarData" :key="'urg' + i" class="up-radar-node">
          <title>{{ g.name }} — {{ g.plays }} {{ $t('stats.plays') }}</title>
          <circle
            :cx="upRadarPt(i, g.pct).x"
            :cy="upRadarPt(i, g.pct).y"
            r="2"
            fill="var(--accent-400)"
          />
          <text
            :x="upRadarLabelPt(i).x"
            :y="upRadarLabelPt(i).y"
            text-anchor="middle"
            class="radar-label radar-label-sm"
          >
            {{ g.name }}
          </text>
          <circle
            :cx="upRadarLabelPt(i).x"
            :cy="upRadarLabelPt(i).y - 3"
            r="14"
            fill="transparent"
          />
        </g>
      </svg>
    </div>
    <div class="up-section">
      <div class="up-stitle">{{ $t('stats.trend') }}</div>
      <div v-if="userProfile.by_library?.length" class="up-trend-bars">
        <div
          v-for="lib in userProfile.by_library"
          :key="lib.name"
          class="up-trend-row"
          :title="lib.name"
        >
          <span class="up-trend-name">{{ lib.name }}</span>
          <div class="up-trend-track">
            <div
              class="up-trend-fill"
              :style="{
                width:
                  Math.round(
                    (lib.count /
                      Math.max(1, ...userProfile.by_library.map(l => l.count))) *
                      100,
                  ) + '%',
              }"
            />
          </div>
          <span class="up-trend-val">{{ lib.count }}</span>
        </div>
      </div>
      <div v-else class="up-empty">{{ $t('stats.noData') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  userProfile: { type: Object, required: true },
})

function fluxClass(m) {
  return m === 'DirectPlay'
    ? 'up-flux-dot--good'
    : m === 'Transcode'
      ? 'up-flux-dot--warn'
      : 'up-flux-dot--info'
}

const upRadarData = computed(() => {
  if (!props.userProfile?.by_genre?.length) return []
  const g = props.userProfile.by_genre
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
  return Array.from({ length: n }, (_, i) => upRadarPt(i, pct))
    .map(p => `${p.x},${p.y}`)
    .join(' ')
}
const upRadarDataPts = computed(() =>
  upRadarData.value
    .map((g, i) => upRadarPt(i, g.pct))
    .map(p => `${p.x},${p.y}`)
    .join(' '),
)
</script>

<style scoped>
.up-col {
  min-width: 0;
  overflow: hidden;
}
.up-section {
  margin-bottom: 12px;
}
.up-stitle {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgb(255, 255, 255, 0.3);
  margin-bottom: 8px;
}
.up-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.up-flux-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
}
.up-flux-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.up-flux-dot--good {
  background: var(--color-success);
}
.up-flux-dot--warn {
  background: var(--color-warning);
}
.up-flux-dot--info {
  background: var(--color-info);
}
.up-flux-name {
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.7);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.up-flux-val {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: rgb(255, 255, 255, 0.5);
  flex-shrink: 0;
}
.up-trend-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.up-trend-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.up-trend-name {
  width: 70px;
  font-size: var(--text-3xs);
  color: rgb(255, 255, 255, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
  text-align: right;
}
.up-trend-track {
  flex: 1;
  height: 8px;
  background: var(--surface-2);
  border-radius: 4px;
  overflow: hidden;
}
.up-trend-fill {
  height: 100%;
  background: linear-gradient(90deg, rgb(var(--accent-rgb), 0.5), rgb(var(--accent-rgb), 0.8));
  border-radius: 4px;
  transition: width var(--duration-slow);
}
.up-trend-val {
  width: 24px;
  font-size: var(--text-3xs);
  font-weight: var(--font-medium);
  color: var(--accent-400);
  text-align: right;
  flex-shrink: 0;
}
.up-radar-svg {
  width: 100%;
  max-width: 260px;
  height: auto;
  display: block;
  margin: 0 auto;
}
.radar-label {
  font-size: 8px;
  fill: rgb(255, 255, 255, 0.5);
  font-weight: var(--font-regular);
}
.radar-label-sm {
  font-size: 7px;
}
</style>
