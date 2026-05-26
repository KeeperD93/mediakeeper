<template>
  <div>
    <div class="totals-row">
      <div class="tot-card" @mouseenter="tiltEnter" @mouseleave="tiltLeave" @mousemove="tiltMove">
        <span class="tot-label">{{ $t('stats.totalPlays') }}</span>
        <span class="tot-value">{{ animPlays }}</span>
        <div class="tot-spark">
          <div
            v-for="(v, i) in sparklinePlays"
            :key="'sp' + i"
            class="spark-bar"
            :style="{ height: sparkH(v, sparklinePlays) + '%' }"
          />
        </div>
        <span class="tot-sub">{{ sparkDelta(sparklinePlays) }}</span>
      </div>
      <div class="tot-card" @mouseenter="tiltEnter" @mouseleave="tiltLeave" @mousemove="tiltMove">
        <span class="tot-label">{{ $t('stats.totalDuration') }}</span>
        <span class="tot-value">{{ ticksToDuration(totals.duration) }}</span>
        <div class="tot-spark">
          <div
            v-for="(v, i) in sparklineDuration"
            :key="'sd' + i"
            class="spark-bar spark-bar-cyan"
            :style="{ height: sparkH(v, sparklineDuration) + '%' }"
          />
        </div>
        <span class="tot-sub">{{ sparkDeltaDuration(sparklineDuration) }}</span>
      </div>
      <div class="tot-card" @mouseenter="tiltEnter" @mouseleave="tiltLeave" @mousemove="tiltMove">
        <span class="tot-label">{{ $t('stats.activeUsers24h') }}</span>
        <span class="tot-value">{{ totals.users24h }}</span>
        <div
          class="tot-avatars"
          :class="{ 'tot-avatars--compact': uniqueSessionUsers.length > 10 }"
          :title="uniqueSessionUsers.map(u => u.id).join(', ')"
        >
          <MkAvatar
            v-for="u in uniqueSessionUsers.slice(0, 30)"
            :key="u.id"
            :src="u.avatar_url"
            :name="u.name"
            :size="24"
            :tier="u.tier"
            class="tot-avatar"
          />
          <div v-if="uniqueSessionUsers.length > 30" class="tot-avatar tot-avatar-more">
            +{{ uniqueSessionUsers.length - 30 }}
          </div>
          <span v-if="!uniqueSessionUsers.length" class="tot-sub tot-sub-inline">
            {{ $t('stats.noConnected') }}
          </span>
        </div>
      </div>
      <div class="tot-card" @mouseenter="tiltEnter" @mouseleave="tiltLeave" @mousemove="tiltMove">
        <span class="tot-label">{{ $t('stats.totalUsers') }}</span>
        <span class="tot-value">{{ totals.totalUsers }}</span>
        <div class="tot-user-breakdown">
          <span class="tot-sub">
            {{ $t('stats.disabled') }} :
            <strong>{{ totals.disabledUsers }}</strong>
          </span>
        </div>
      </div>
      <div class="tot-card" @mouseenter="tiltEnter" @mouseleave="tiltLeave" @mousemove="tiltMove">
        <span class="tot-label">{{ $t('stats.transcoding') }}</span>
        <span class="tot-value">{{ totals.transcodePct }}%</span>
        <div class="transcode-bar">
          <div class="transcode-fill" :style="{ width: totals.transcodePct + '%' }" />
        </div>
        <span class="tot-sub">
          {{ $t('stats.directPlay') }} : {{ (100 - totals.transcodePct).toFixed(1) }}%
        </span>
      </div>
    </div>

    <div v-if="records" class="records-ribbon">
      <div class="rec-item">
        <Zap class="rec-icon" :size="14" />
        <span class="rec-label has-tooltip" :data-tooltip="$t('stats.recordTooltip')">
          {{ $t('stats.record') }}
        </span>
        <span class="rec-value">{{ records.record_day_count }}</span>
        <span class="rec-sub">
          {{ $t('stats.recordOn', { date: fmtRecordDate(records.record_day_date) }) }}
        </span>
      </div>
      <div class="rec-sep" />
      <div class="rec-item">
        <Flame class="rec-icon rec-icon-streak" :size="14" />
        <span class="rec-label has-tooltip" :data-tooltip="$t('stats.streakTooltip')">
          {{ $t('stats.streak') }}
        </span>
        <span class="rec-value">{{ records.current_streak }}{{ $t('stats.daysShort') }}</span>
        <span class="rec-sub">{{ $t('stats.streakRecord', { n: records.longest_streak }) }}</span>
      </div>
      <div class="rec-sep" />
      <div class="rec-item">
        <User class="rec-icon" :size="14" />
        <span class="rec-label has-tooltip" :data-tooltip="$t('stats.topUserTooltip')">
          {{ $t('stats.topUser') }}
        </span>
        <span class="rec-value">{{ records.top_user_name }}</span>
        <span class="rec-sub">{{ records.top_user_pct }}%</span>
      </div>
      <div class="rec-sep" />
      <div class="rec-item">
        <Clock class="rec-icon" :size="14" />
        <span class="rec-label has-tooltip" :data-tooltip="$t('stats.peakHourTooltip')">
          {{ $t('stats.peakHour') }}
        </span>
        <span class="rec-value">{{ records.peak_hour }}h</span>
        <span class="rec-sub">{{ records.peak_hour_count }} {{ $t('stats.plays_unit') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { Clock, Flame, User, Zap } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'

const { t } = useI18n()
const { totals, sparklinePlays, sparklineDuration, records, minimap24h, ticksToDuration } =
  useStats()

const uniqueSessionUsers = computed(() => {
  const seen = new Set()
  return minimap24h.value
    .filter(s => {
      const key = s.user_id || s.user || '?'
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    .map(s => ({
      id: s.user_id || s.user || '?',
      name: s.user || '?',
      avatar_url: s.avatar_url || null,
      tier: s.tier || 'bronze',
    }))
})

function sparkH(v, arr) {
  const mx = Math.max(...arr, 1)
  return Math.round((v / mx) * 100)
}
function _weekSlice(arr) {
  if (!arr || !arr.length) return []
  const today = new Date()
  const dayIdx = (today.getDay() + 6) % 7
  return arr.slice(-Math.min(dayIdx + 1, arr.length))
}
function sparkDelta(arr) {
  const total = _weekSlice(arr).reduce((s, v) => s + v, 0)
  if (total <= 0) return t('stats.noPlaysThisWeek')
  return t('stats.deltaThisWeek', { value: total })
}
function sparkDeltaDuration(arr) {
  const totalTicks = _weekSlice(arr).reduce((s, v) => s + v, 0)
  if (totalTicks <= 0) return t('stats.noPlaysThisWeek')
  const abs = totalTicks / 10000000
  const h = Math.floor(abs / 3600)
  const m = Math.floor((abs % 3600) / 60)
  let txt
  if (h >= 1 && m > 0) txt = `${h}h${String(m).padStart(2, '0')}`
  else if (h >= 1) txt = `${h}h`
  else txt = `${m} min`
  return t('stats.deltaThisWeek', { value: txt })
}

const animPlays = ref('0')
let counterAnim = null
function animateCounter(target) {
  if (counterAnim) cancelAnimationFrame(counterAnim)
  const start = parseInt(String(animPlays.value).replace(/\s/g, '')) || 0
  const d = target - start
  if (!d) {
    animPlays.value = target.toLocaleString(undefined)
    return
  }
  const t0 = performance.now()
  function step(ts) {
    const p = Math.min((ts - t0) / 800, 1)
    animPlays.value = Math.round(start + d * (1 - Math.pow(1 - p, 3))).toLocaleString(undefined)
    if (p < 1) counterAnim = requestAnimationFrame(step)
  }
  counterAnim = requestAnimationFrame(step)
}
watch(
  () => totals.plays,
  v => animateCounter(v || 0),
  { immediate: true },
)

function tiltMove(e) {
  const r = e.currentTarget.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width - 0.5
  const y = (e.clientY - r.top) / r.height - 0.5
  e.currentTarget.style.transform = `perspective(600px) rotateX(${(-y * 6).toFixed(1)}deg) rotateY(${(x * 6).toFixed(1)}deg)`
  e.currentTarget.style.transition = 'none'
}
function tiltLeave(e) {
  e.currentTarget.style.transform = ''
  e.currentTarget.style.transition = 'transform 0.4s ease-out'
}
function tiltEnter(e) {
  e.currentTarget.style.transition = 'none'
}

function fmtRecordDate(d) {
  if (!d) return '—'
  const p = d.split('-')
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d
}

onUnmounted(() => {
  if (counterAnim) cancelAnimationFrame(counterAnim)
})
</script>

<style scoped>
.totals-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.tot-card {
  background: var(--surface-1);
  backdrop-filter: var(--blur-md);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  position: relative;
  overflow: hidden;
  cursor: default;
  will-change: transform;
  transition:
    transform 0.4s ease-out,
    border-color var(--duration-base);
}
.tot-card:hover {
  border-color: rgb(var(--accent-rgb), 0.2);
}
.tot-label {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: rgb(255, 255, 255, 0.35);
  display: block;
}
.tot-value {
  font-size: 1.6rem;
  font-weight: var(--font-medium);
  color: var(--text-primary);
  display: block;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.tot-spark {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 28px;
  margin-top: 8px;
}
.spark-bar {
  flex: 1;
  background: rgb(var(--accent-rgb), 0.35);
  border-radius: 2px 2px 0 0;
  min-width: 0;
  transition: height var(--duration-slow);
}
.spark-bar-cyan {
  background: rgb(6, 182, 212, 0.35);
}
.tot-sub {
  font-size: var(--text-3xs);
  color: rgb(255, 255, 255, 0.3);
  margin-top: 6px;
  display: block;
}
.tot-sub-inline {
  margin: 0;
}
.tot-avatars {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 6px;
  margin-top: 10px;
  max-width: calc(10 * 26px + 9 * 6px);
}
.tot-avatars--compact {
  grid-template-columns: repeat(15, 1fr);
  gap: 4px;
  max-width: calc(15 * 18px + 14 * 4px);
}
.tot-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.tot-avatars--compact .tot-avatar {
  width: 18px;
  height: 18px;
  font-size: 0.5rem;
}
.tot-avatar-more {
  background: rgb(255, 255, 255, 0.12);
  color: var(--text-secondary);
  font-size: 0.58rem;
}
.tot-avatars--compact .tot-avatar-more {
  font-size: 0.48rem;
}
.transcode-bar {
  height: 6px;
  background: var(--surface-2);
  border-radius: 3px;
  margin-top: 10px;
  overflow: hidden;
}
.transcode-fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b, var(--color-warning));
  border-radius: 3px;
  transition: width var(--duration-slower);
}

.records-ribbon {
  display: flex;
  align-items: center;
  background: rgb(255, 255, 255, 0.02);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 12px 20px;
  margin-bottom: 24px;
}
.rec-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.rec-icon {
  color: var(--accent-400);
  flex-shrink: 0;
}
.rec-icon-streak {
  color: #f59e0b;
}
.rec-label {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgb(255, 255, 255, 0.3);
  flex-shrink: 0;
}
.has-tooltip {
  position: relative;
  cursor: help;
  border-bottom: 1px dotted rgb(255, 255, 255, 0.2);
}
.has-tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-6px);
  background: rgb(15, 20, 35, 0.95);
  color: var(--text-primary);
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--duration-base);
  border: 1px solid rgb(255, 255, 255, 0.1);
  z-index: 50;
  text-transform: none;
  font-weight: normal;
  letter-spacing: normal;
  box-shadow: 0 4px 12px rgb(0, 0, 0, 0.3);
  visibility: hidden;
}
.has-tooltip:hover::after {
  opacity: 1;
  visibility: visible;
}
.rec-item:first-child .has-tooltip::after {
  left: 0;
  transform: translateY(-6px);
}
.rec-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  white-space: nowrap;
}
.rec-sub {
  font-size: var(--text-3xs);
  color: var(--text-very-faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rec-sep {
  width: 1px;
  height: 28px;
  background: var(--surface-3);
  margin: 0 12px;
  flex-shrink: 0;
}

@media (max-width: 1280px) {
  .totals-row {
    grid-template-columns: repeat(3, 1fr);
  }
  .records-ribbon {
    flex-wrap: wrap;
    gap: 8px;
  }
  .rec-sep {
    display: none;
  }
}
@media (max-width: 768px) {
  .totals-row {
    grid-template-columns: 1fr;
  }
  /* Mobile: stack record items vertically so the icon, label, value
     and sub-text never overlap on narrow screens. */
  .records-ribbon {
    flex-direction: column;
    align-items: stretch;
    padding: 10px 14px;
    gap: 0;
  }
  .rec-item {
    flex: 1 1 auto;
    width: 100%;
    flex-wrap: wrap;
    padding: 8px 0;
  }
  .rec-item:not(:last-child) {
    border-bottom: 0.5px solid var(--border-subtle);
  }
  .rec-value {
    margin-left: auto;
  }
  .rec-sub {
    flex-basis: 100%;
    padding-left: 22px;
  }
}
</style>
