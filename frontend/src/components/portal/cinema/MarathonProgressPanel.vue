<template>
  <aside
    v-if="visible"
    class="pt-cr-marathon"
    :aria-live="ready ? 'polite' : 'off'"
  >
    <header class="pt-cr-marathon-head">
      <Film :size="14" :stroke-width="2.5" />
      <span>{{ headerLabel }}</span>
    </header>
    <ul class="pt-cr-marathon-list">
      <li v-for="p in participants" :key="p.user_id" class="pt-cr-marathon-row">
        <span class="pt-cr-marathon-name">
          {{ p.display_name }}
          <span
            v-if="isMarathon && p.user_step != null && p.user_step < currentStep"
            class="pt-cr-marathon-late"
          >
            {{ $t('portal.cinema.marathon.late') }}
          </span>
        </span>
        <div
          class="pt-cr-marathon-bar"
          :aria-label="$t('portal.cinema.marathon.barAria', {
            name: p.display_name,
            percent: pct(p.ratio),
          })"
        >
          <div
            class="pt-cr-marathon-bar-fill"
            :style="{ width: pct(p.ratio) + '%' }"
          />
          <div
            v-if="p.meets_threshold"
            class="pt-cr-marathon-bar-done"
            aria-hidden="true"
          >
            <Check :size="10" :stroke-width="3" />
          </div>
        </div>
        <span class="pt-cr-marathon-time">
          <template v-if="isMarathon && p.user_step != null">
            {{ p.user_step + 1 }}/{{ totalSteps }}
          </template>
          <template v-else>{{ formatRemaining(p.seconds_remaining) }}</template>
        </span>
      </li>
    </ul>
    <p
      v-if="ineligibleCount > 0"
      class="pt-cr-marathon-ineligible"
    >
      {{ $t('portal.cinema.marathon.ineligible', ineligibleCount, { count: ineligibleCount }) }}
    </p>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, Film } from 'lucide-vue-next'

const props = defineProps({
  progress: { type: Object, default: null },
})

const { t } = useI18n()

const isMarathon = computed(() => Boolean(props.progress?.is_marathon))
const currentStep = computed(() => props.progress?.current_step ?? 0)
const totalSteps = computed(() => props.progress?.total_steps ?? 0)
const participants = computed(() => props.progress?.participants ?? [])
const ineligibleCount = computed(() => props.progress?.ineligible_count ?? 0)
const ready = computed(() => Boolean(props.progress?.ready))

// The panel surfaces in two shapes:
//   * Marathon — always visible (even pre-launch) so the X/Y header,
//     ineligible-count notice and per-user "En retard" tags can warn
//     viewers about state they need to know about.
//   * Single-film — visible only once at least one participant has a
//     live playback session, so the room stays clean while everyone is
//     waiting for the countdown.
const visible = computed(() => {
  if (!props.progress) return false
  return isMarathon.value || participants.value.length > 0
})

const headerLabel = computed(() => {
  if (isMarathon.value) {
    return t('portal.cinema.marathon.title', {
      current: currentStep.value + 1,
      total: totalSteps.value,
    })
  }
  return t('portal.cinema.playback.title')
})

function pct(ratio) {
  const r = Number.isFinite(ratio) ? ratio : 0
  return Math.min(100, Math.max(0, Math.round(r * 100)))
}

function formatRemaining(seconds) {
  if (seconds == null) return '—'
  if (seconds <= 0) return '0 min'
  const totalMinutes = Math.floor(seconds / 60)
  if (totalMinutes >= 60) {
    const h = Math.floor(totalMinutes / 60)
    const m = totalMinutes % 60
    return `${h}h ${String(m).padStart(2, '0')}`
  }
  return `${totalMinutes} min`
}

defineExpose({ pct, formatRemaining })
</script>

<style scoped>
.pt-cr-marathon {
  position: absolute;
  bottom: 80px;
  left: 12px;
  /* Sits above the seats (z-index 5) and the seat bubbles aren't an
     issue (bubbles are 30 and we never overlap them — they bloom from
     a seat going up, marathon panel is bottom-left). Still below the
     HUD (12) and the launch CTA (15). */
  z-index: 10;
  width: 260px;
  max-width: 92vw;
  padding: 10px 12px 12px;
  background: rgb(0, 0, 0, 0.55);
  border: 1px solid var(--portal-border-strong);
  border-radius: var(--portal-radius-md);
  color: var(--portal-text-primary);
  backdrop-filter: blur(8px);
  font-size: 12px;
}

.pt-cr-marathon-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 8px;
  color: rgb(255, 255, 255, 0.96);
}

.pt-cr-marathon-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pt-cr-marathon-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1fr 40px;
  align-items: center;
  gap: 8px;
}

.pt-cr-marathon-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgb(255, 255, 255, 0.88);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.pt-cr-marathon-late {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: var(--portal-font-bold);
  padding: 1px 6px;
  border-radius: var(--portal-radius-pill);
  background: rgb(var(--portal-color-warning-rgb), 0.22);
  color: var(--portal-color-warning);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.pt-cr-marathon-bar {
  position: relative;
  height: 4px;
  background: var(--portal-surface-5);
  border-radius: 2px;
  overflow: hidden;
}

.pt-cr-marathon-bar-fill {
  height: 100%;
  background: var(--accent-500);
  transition: width 0.3s ease;
}

.pt-cr-marathon-bar-done {
  position: absolute;
  top: 50%;
  right: 2px;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  display: grid;
  place-items: center;
  color: var(--portal-color-success);
}

.pt-cr-marathon-time {
  text-align: right;
  color: rgb(255, 255, 255, 0.65);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
}

.pt-cr-marathon-ineligible {
  margin: 8px 0 0;
  color: rgb(255, 255, 255, 0.6);
  font-size: 11px;
  line-height: 1.3;
}

@media (max-width: 640px) {
  .pt-cr-marathon {
    bottom: 64px;
    left: 8px;
    width: calc(100vw - 16px);
  }
}
</style>
