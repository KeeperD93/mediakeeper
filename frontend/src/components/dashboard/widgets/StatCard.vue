<template>
  <div
    class="wg-stat"
    :class="{ 'wg-stat-click': clickable && !editing, 'wg-stat-glow-red': glowRed }"
    :style="[tiltStyle, accentVars]"
    @click="onClick"
    @mousemove="onTilt"
    @mouseleave="resetTilt"
  >
    <div class="wg-stat-body">
      <div v-if="icon" class="wg-stat-icon" :class="{ 'wg-stat-icon-skel': isLoading }">
        <component :is="icon" v-if="!isLoading" :size="20" :stroke-width="2" />
      </div>
      <div class="wg-stat-text">
        <!-- Skeleton shimmer when loading -->
        <template v-if="isLoading">
          <div class="wg-skel-label" />
          <div class="wg-skel-val" />
        </template>
        <!-- Actual content -->
        <template v-else>
          <span class="wg-stat-label">{{ label }}</span>
          <span class="wg-stat-val" :style="valStyle">{{ displayValue }}</span>
        </template>
      </div>
    </div>

    <!-- Glow orb -->
    <div class="wg-glow" :style="glowStyle" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { STAT_CARD_ACCENT } from '@/constants/dashboardStatColors'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  route: { type: String, default: '' },
  color: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  accent: { type: String, default: STAT_CARD_ACCENT.plays },
  editing: { type: Boolean, default: false },
})

/* ``accent`` always drives the icon frame + ambient glow (the "module"
 * colour of the card). ``color`` only repaints the numeric value
 * (alert state, e.g. duplicates count > 0). ``--wg-hover`` follows
 * ``color`` when set so the hover border + glow reflect the alert
 * state (red on issues, green on zero) — otherwise falls back to the
 * accent for the default "everything fine" hover. */
const accentVars = computed(() => ({
  '--wg-accent': props.accent,
  '--wg-hover': props.color || props.accent,
}))

const router = useRouter()
const clickable = !!props.route
/* Reactive style — props.color flips after the data load resolves
 * (e.g. duplicates count goes from "—" to "5", which paints the value
 * red). A frozen object would lock the colour to whatever was set at
 * mount and miss the alert-state transition. */
const valStyle = computed(() => (props.color ? { color: props.color } : {}))
const glowRed = computed(() => props.color === STAT_CARD_ACCENT.duplicates)
const isLoading = computed(() => props.value == null || props.value === '—')

// ---- Animated counter ----
const displayValue = ref('—')
const animFrame = ref(null)

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function parseNumeric(val) {
  if (val == null || val === '—') return null
  const s = String(val).replace(/\s/g, '').replace(',', '.')
  const n = parseFloat(s)
  return isNaN(n) ? null : n
}

function formatLike(target, num) {
  const s = String(target)
  const suffix = s.replace(/^[\d\s.,]+/, '')
  const decMatch = s.match(/[.,](\d+)/)
  const dec = decMatch ? decMatch[1].length : 0
  const formatted = num.toLocaleString(undefined, {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  })
  return formatted + suffix
}

function animateCounter(target) {
  const num = parseNumeric(target)
  if (num === null || num === 0 || prefersReducedMotion()) {
    displayValue.value = target
    return
  }
  const duration = 900
  const start = performance.now()
  function tick(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    const current = num * eased
    displayValue.value = formatLike(target, current)
    if (progress < 1) animFrame.value = requestAnimationFrame(tick)
  }
  if (animFrame.value) cancelAnimationFrame(animFrame.value)
  animFrame.value = requestAnimationFrame(tick)
}

onMounted(() => {
  if (props.value && props.value !== '—') animateCounter(props.value)
})

watch(
  () => props.value,
  val => {
    if (val && val !== '—') animateCounter(val)
    else displayValue.value = val
  },
)

// ---- 3D tilt ----
const tiltX = ref(0)
const tiltY = ref(0)
const tiltStyle = computed(() => ({
  transform: `perspective(600px) rotateX(${tiltX.value}deg) rotateY(${tiltY.value}deg)`,
  transition: tiltX.value === 0 && tiltY.value === 0 ? 'transform 0.4s ease-out' : 'none',
}))

function onTilt(e) {
  if (props.editing || prefersReducedMotion()) return
  const rect = e.currentTarget.getBoundingClientRect()
  const x = (e.clientX - rect.left) / rect.width - 0.5
  const y = (e.clientY - rect.top) / rect.height - 0.5
  tiltY.value = +(x * 8).toFixed(2)
  tiltX.value = +(-y * 8).toFixed(2)
}
function resetTilt() {
  tiltX.value = 0
  tiltY.value = 0
}

// ---- Glow ----
function hexToRgba(hex, alpha) {
  const m = hex.replace('#', '').match(/.{2}/g)
  if (!m) return `rgba(99,102,241,${alpha})`
  const [r, g, b] = m.map(h => parseInt(h, 16))
  return `rgba(${r},${g},${b},${alpha})`
}
const glowStyle = computed(() => {
  const c = props.color || props.accent
  return { background: `radial-gradient(circle, ${hexToRgba(c, 0.14)} 0%, transparent 70%)` }
})

function onClick() {
  if (props.editing || !props.route) return
  router.push(props.route)
}
</script>

<style scoped>
.wg-stat {
  background: var(--card-bg);
  border-radius: var(--radius-card);
  padding: var(--space-2) var(--space-3);
  border: var(--border-width-thin) solid var(--border-default);
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
  min-width: 0;
  position: relative;
  transition:
    border-color var(--duration-base),
    box-shadow var(--duration-slow);
  will-change: transform;
}
.wg-stat-click {
  cursor: pointer;
}
.wg-stat:hover {
  border-color: color-mix(in srgb, var(--wg-hover) 35%, transparent);
  box-shadow:
    0 0 24px color-mix(in srgb, var(--wg-hover) 12%, transparent),
    0 0 60px color-mix(in srgb, var(--wg-hover) 4%, transparent),
    inset 0 0 20px color-mix(in srgb, var(--wg-hover) 4%, transparent);
}
.wg-stat-body {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  position: relative;
  z-index: 1;
  min-width: 0;
}
.wg-stat-icon {
  flex-shrink: 0;
  width: var(--icon-frame-md);
  height: var(--icon-frame-md);
  border-radius: var(--radius-card);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--wg-accent, var(--accent-500));
  background: color-mix(in srgb, var(--wg-accent) 18%, transparent);
  border: var(--border-width) solid color-mix(in srgb, var(--wg-accent) 28%, transparent);
  transition:
    background var(--duration-base),
    border-color var(--duration-base),
    transform var(--duration-base);
}
.wg-stat:hover .wg-stat-icon {
  background: color-mix(in srgb, var(--wg-accent) 26%, transparent);
  border-color: color-mix(in srgb, var(--wg-accent) 45%, transparent);
  transform: scale(1.05);
}
.wg-stat-icon-skel {
  background: var(--surface-2);
  border-color: var(--border-default);
}
.wg-stat-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.wg-stat-label {
  display: block;
  font-size: var(--text-2xs);
  line-height: var(--lh-snug-tight);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wg-stat-val {
  display: block;
  font-size: var(--text-lg);
  font-weight: var(--font-regular);
  line-height: var(--lh-tight);
  color: var(--text-primary);
  margin-top: var(--space-half);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Skeleton shimmer */
.wg-skel-label,
.wg-skel-val {
  border-radius: var(--radius-sm);
  background: var(--gradient-skeleton-shimmer);
  background-size: 200% 100%;
  animation: wg-shimmer var(--duration-animation) ease-in-out infinite;
}
.wg-skel-label {
  width: 60%;
  height: 12px;
}
.wg-skel-val {
  width: 45%;
  height: 24px;
  margin-top: 6px;
}
@keyframes wg-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Ambient glow orb */
.wg-glow {
  position: absolute;
  inset: -20%;
  border-radius: var(--radius-circle);
  opacity: 0;
  transition: opacity var(--duration-slower);
  pointer-events: none;
  z-index: 0;
}
.wg-stat:hover .wg-glow {
  opacity: 1;
}

/* Reduced-motion: instant hover state, no animated fades (the JS 3D tilt
   and the count-up are short-circuited in script). */
@media (prefers-reduced-motion: reduce) {
  .wg-stat,
  .wg-stat-icon,
  .wg-glow {
    transition: none;
  }
}
</style>
