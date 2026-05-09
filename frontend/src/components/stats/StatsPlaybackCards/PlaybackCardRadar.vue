<template>
  <div>
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
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  byGenre: { type: Array, default: () => [] },
})

const radarSize = 360,
  radarCx = 180,
  radarCy = 180,
  radarR = 115
const genreRadarData = computed(() => {
  const g = props.byGenre || []
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
</style>
