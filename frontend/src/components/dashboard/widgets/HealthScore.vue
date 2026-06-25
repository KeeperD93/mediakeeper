<template>
  <div
    class="wg-health"
    :class="{ 'wg-health-click': !editing }"
    :style="{ '--wg-hover': hoverColor }"
    @click="goToPage"
  >
    <!-- Ambient glow orb (radial gradient revealed on hover) — mirrors
         the ``.wg-glow`` element of StatCard so the hover signal feels
         identical across both widget shapes. Rendered before the
         conditional skeleton/content branch so it does not break the
         v-if / v-else adjacency. -->
    <div class="wg-h-glow" />

    <!-- Skeleton -->
    <template v-if="loading">
      <div class="wg-h-skel-ring" />
      <div class="wg-h-skel-lines">
        <div class="wg-h-skel-l1" />
        <div class="wg-h-skel-l2" />
      </div>
    </template>

    <!-- Content -->
    <template v-else>
      <div class="wg-h-ring-wrap">
        <svg viewBox="0 0 80 80" class="wg-h-ring">
          <circle cx="40" cy="40" r="34" fill="none" stroke-width="6" class="wg-h-ring-track" />
          <circle
            cx="40"
            cy="40"
            r="34"
            fill="none"
            :style="{ stroke: ringColor }"
            stroke-width="6"
            stroke-linecap="round"
            :stroke-dasharray="dashArray"
            :stroke-dashoffset="dashOffset"
            transform="rotate(-90 40 40)"
            class="wg-h-arc"
          />
        </svg>
        <span class="wg-h-score" :style="{ color: ringColor }">{{ score }}</span>
      </div>
      <div class="wg-h-info">
        <span class="wg-h-label">{{ $t('healthCheck.title') }}</span>
        <span v-if="summary" class="wg-h-counts">
          <span
            v-if="summary.critical"
            class="wg-h-badge wg-h-crit"
            :title="$t('healthCheck.critical')"
          >
            {{ summary.critical }}
          </span>
          <span
            v-if="summary.warning"
            class="wg-h-badge wg-h-warn"
            :title="$t('healthCheck.warning')"
          >
            {{ summary.warning }}
          </span>
          <span v-if="summary.info" class="wg-h-badge wg-h-info-b" :title="$t('healthCheck.info')">
            {{ summary.info }}
          </span>
          <span v-if="!summary.critical && !summary.warning && !summary.info" class="wg-h-ok">
            {{ $t('healthCheck.allGood') }}
          </span>
        </span>
        <span v-else class="wg-h-sub">{{ $t('healthCheck.noScan') }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { STAT_STATE_COLOR } from '@/constants/dashboardStatColors'

const props = defineProps({
  editing: { type: Boolean, default: false },
})

const { apiGet } = useApi()
const router = useRouter()
const summary = ref(null)
const loading = ref(true)

const score = computed(() => summary.value?.score ?? '—')

const ringColor = computed(() => {
  const s = summary.value?.score ?? 100
  if (s >= 80) return 'var(--color-success)'
  if (s >= 50) return 'var(--color-warning)'
  return 'var(--color-error)'
})

/* Hover border + glow follow a binary positive/negative state:
 *   score === 100 → positive (green)
 *   anything else → negative (red)
 * Distinct from ``ringColor`` which has the 80 / 50 thresholds for the
 * arc itself. */
const hoverColor = computed(() =>
  summary.value?.score === 100 ? STAT_STATE_COLOR.ok : STAT_STATE_COLOR.alert,
)

const circumference = 2 * Math.PI * 34
const dashArray = `${circumference}`
const dashOffset = computed(() => {
  const s = summary.value?.score ?? 0
  return circumference - (circumference * s) / 100
})

function goToPage() {
  if (!props.editing) router.push('/health')
}

onMounted(async () => {
  try {
    const d = await apiGet('/api/healthcheck/summary')
    if (d && d.score !== undefined) summary.value = d
  } catch {
    /* silent: widget fetch, card stays blank */
  }
  loading.value = false
})
</script>

<style scoped>
.wg-health {
  background: var(--card-bg);
  border-radius: var(--radius-card);
  padding: var(--space-3) var(--space-3-5);
  border: var(--border-width-thin) solid var(--border-default);
  height: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  /* No overflow: hidden — the hover box-shadow (24px + 60px outset glow)
     would be clipped, breaking visual parity with .wg-stat. */
  position: relative;
  transition:
    var(--transition-border),
    box-shadow var(--duration-slow);
}
.wg-health-click {
  cursor: pointer;
}
@media (hover: hover) {
  .wg-health:hover {
    border-color: color-mix(in srgb, var(--wg-hover) 35%, transparent);
    box-shadow:
      0 0 24px color-mix(in srgb, var(--wg-hover) 12%, transparent),
      0 0 60px color-mix(in srgb, var(--wg-hover) 4%, transparent),
      inset 0 0 20px color-mix(in srgb, var(--wg-hover) 4%, transparent);
  }
}

/* Ambient glow orb — same pattern as .wg-glow in StatCard. Revealed
   on hover so the hover signal is visually identical to the four
   stat cards (icon-frame siblings). */
.wg-h-glow {
  position: absolute;
  inset: -20%;
  border-radius: var(--radius-circle);
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--wg-hover) 14%, transparent) 0%,
    transparent 70%
  );
  opacity: 0;
  transition: opacity var(--duration-slower);
  pointer-events: none;
  z-index: 0;
}
@media (hover: hover) {
  .wg-health:hover .wg-h-glow {
    opacity: 1;
  }
}

.wg-h-ring-wrap {
  position: relative;
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  /* Stack above the ambient glow orb (.wg-h-glow at z-index: 0). */
  z-index: 1;
}
.wg-h-ring {
  width: 100%;
  height: 100%;
}
.wg-h-ring-track {
  stroke: var(--border-subtle);
}
.wg-h-arc {
  transition:
    stroke-dashoffset var(--duration-slower) ease-out,
    stroke var(--duration-slow);
}
.wg-h-score {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  letter-spacing: var(--tracking-tight);
}

.wg-h-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
  position: relative;
  z-index: 1;
}
.wg-h-label {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wg-h-counts {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-wrap: wrap;
}
.wg-h-badge {
  font-size: var(--text-3xs);
  font-weight: var(--font-medium);
  padding: var(--space-half) 7px;
  border-radius: var(--radius-sm);
  line-height: var(--lh-compact);
}
.wg-h-crit {
  background: rgb(var(--color-error-strong-rgb), 0.15);
  color: var(--color-error-light);
}
.wg-h-warn {
  background: rgb(var(--color-warning-rgb), 0.15);
  color: var(--color-warning);
}
.wg-h-info-b {
  background: rgb(var(--color-info-rgb), 0.15);
  color: var(--color-info);
}
.wg-h-ok {
  font-size: var(--text-2xs);
  color: var(--color-success);
  font-weight: var(--font-regular);
}
.wg-h-sub {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}

/* Skeleton */
.wg-h-skel-ring {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-circle);
  flex-shrink: 0;
  background: var(--gradient-skeleton-shimmer);
  background-size: 200% 100%;
  animation: wg-h-shim var(--duration-animation) ease-in-out infinite;
}
.wg-h-skel-lines {
  display: flex;
  flex-direction: column;
  gap: var(--space-half);
}
.wg-h-skel-l1,
.wg-h-skel-l2 {
  border-radius: var(--radius-sm);
  height: 10px;
  background: var(--gradient-skeleton-shimmer);
  background-size: 200% 100%;
  animation: wg-h-shim var(--duration-animation) ease-in-out infinite;
}
.wg-h-skel-l1 {
  width: 60px;
}
.wg-h-skel-l2 {
  width: 80px;
}
@keyframes wg-h-shim {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Reduced-motion: drop the decorative hover / glow / arc transitions. */
@media (prefers-reduced-motion: reduce) {
  .wg-health,
  .wg-h-glow,
  .wg-h-arc {
    transition: none;
  }
}
</style>
