<template>
  <div class="wg-health" :class="{ 'wg-health-click': !editing }" @click="goToPage">
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
          <circle
            cx="40"
            cy="40"
            r="34"
            fill="none"
            stroke-width="6"
            class="wg-h-ring-track"
          />
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
          <span v-if="summary.critical" class="wg-h-badge wg-h-crit">{{ summary.critical }}</span>
          <span v-if="summary.warning" class="wg-h-badge wg-h-warn">{{ summary.warning }}</span>
          <span v-if="summary.info" class="wg-h-badge wg-h-info-b">{{ summary.info }}</span>
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
  background: var(--card-bg, var(--surface-1));
  border-radius: var(--radius-card);
  padding: 12px 14px;
  border: 0.5px solid var(--border-default);
  height: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  overflow: hidden;
  position: relative;
  transition:
    border-color 0.25s,
    box-shadow 0.35s;
}
.wg-health-click {
  cursor: pointer;
}
.wg-health:hover {
  border-color: rgb(var(--color-success-rgb), 0.25);
  box-shadow: 0 0 24px rgb(var(--color-success-rgb), 0.08);
}

.wg-h-ring-wrap {
  position: relative;
  width: 56px;
  height: 56px;
  flex-shrink: 0;
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
    stroke-dashoffset 1s ease-out,
    stroke 0.4s;
}
.wg-h-score {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  letter-spacing: -0.5px;
}

.wg-h-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.wg-h-label {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wg-h-counts {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}
.wg-h-badge {
  font-size: var(--text-3xs);
  font-weight: var(--font-medium);
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  line-height: var(--lh-compact);
}
.wg-h-crit {
  background: rgb(244, 63, 94, 0.15);
  color: #fb7185;
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
  border-radius: 50%;
  flex-shrink: 0;
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.03) 25%,
    rgb(255, 255, 255, 0.07) 50%,
    rgb(255, 255, 255, 0.03) 75%
  );
  background-size: 200% 100%;
  animation: wg-h-shim var(--duration-animation) ease-in-out infinite;
}
.wg-h-skel-lines {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.wg-h-skel-l1,
.wg-h-skel-l2 {
  border-radius: 4px;
  height: 10px;
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.03) 25%,
    rgb(255, 255, 255, 0.07) 50%,
    rgb(255, 255, 255, 0.03) 75%
  );
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
</style>
