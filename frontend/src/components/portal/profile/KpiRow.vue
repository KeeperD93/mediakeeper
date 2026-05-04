<template>
  <div class="gc-kpis">
    <div class="gc-kpi gc-kpi--accent">
      <div class="gc-kpi-val">
        <CountUp :value="stats.total_plays || 0" :delay="0" />
      </div>
      <div class="gc-kpi-lbl">{{ $t('portal.profile.totalPlays') }}</div>
    </div>
    <div class="gc-kpi gc-kpi--warm">
      <div class="gc-kpi-val">
        <CountUp :value="stats.total_minutes || 0" :delay="60" :formatter="minutesFormatter" />
      </div>
      <div class="gc-kpi-lbl">{{ $t('portal.profile.totalTime') }}</div>
      <div v-if="stats.total_minutes > 60" class="gc-kpi-fun">{{ funTimeComparison }}</div>
    </div>
    <div class="gc-kpi gc-kpi--fire">
      <div class="gc-kpi-val">
        <Flame :size="18" class="gc-kpi-flame" />
        <CountUp :value="stats.streak || 0" :delay="120" />
      </div>
      <div class="gc-kpi-lbl">{{ $t('portal.profile.streak') }}</div>
    </div>
    <div v-if="stats.record_day?.count" class="gc-kpi gc-kpi--gold">
      <div class="gc-kpi-val">
        <CountUp :value="stats.record_day.count" :delay="180" />
      </div>
      <div class="gc-kpi-lbl">{{ $t('portal.profile.recordDay') }}</div>
      <div class="gc-kpi-fun">{{ stats.record_day.date }}</div>
    </div>
    <div v-if="stats.most_rewatched" class="gc-kpi gc-kpi--purple">
      <div class="gc-kpi-val">
        <CountUp :value="stats.most_rewatched.count" :delay="240" :formatter="xFormatter" />
      </div>
      <div class="gc-kpi-lbl">{{ stats.most_rewatched.title }}</div>
      <div class="gc-kpi-fun">{{ $t('portal.profile.mostRewatched') }}</div>
    </div>
  </div>
</template>

<script setup>
import { Flame } from 'lucide-vue-next'
import CountUp from '@/components/portal/CountUp.vue'

const props = defineProps({
  stats: { type: Object, required: true },
  funTimeComparison: { type: String, default: '' },
  formatTime: { type: Function, required: true },
})

// Apply the caller's formatTime to the animated minute counter so the
// unit (h / min) matches what the rest of the page displays.
function minutesFormatter(n) {
  return props.formatTime(Math.round(n))
}

function xFormatter(n) {
  return `${Math.round(n)}×`
}
</script>

<style>
@import url('@/assets/styles/portal/kpis.css');
</style>
