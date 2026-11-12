/**
 * Animate a counter from 0 to ``target`` over ``duration`` ms using a
 * requestAnimationFrame loop, and again each time ``target`` changes when it
 * is a ref. Honors ``prefers-reduced-motion`` by snapping straight to the
 * final value, a count under way included when the setting is turned on.
 *
 * Surfaces a Vue ref ``displayed`` that components can render with
 * ``toLocaleString()`` to feed the hero billboard / live stats bar
 * count-up effect.
 */
import { onBeforeUnmount, onMounted, ref, toValue, watch } from 'vue'
import { usePrefersReducedMotion } from '@/composables/usePrefersReducedMotion'

const EASING = {
  easeOutQuart: t => 1 - Math.pow(1 - t, 4),
  linear: t => t,
}

export function useCountUp(target, { duration = 1200, easing = 'easeOutQuart' } = {}) {
  // Read on mount before the first count below: its hook runs first.
  const reducedMotion = usePrefersReducedMotion()
  const displayed = ref(0)
  const easeFn = EASING[easing] || EASING.easeOutQuart
  let rafId = null
  let startedAt = 0

  function step(now) {
    const elapsed = now - startedAt
    if (duration <= 0 || elapsed >= duration) {
      displayed.value = toValue(target)
      rafId = null
      return
    }
    const t = elapsed / duration
    displayed.value = Math.round(toValue(target) * easeFn(t))
    rafId = requestAnimationFrame(step)
  }

  function finish() {
    if (rafId) cancelAnimationFrame(rafId)
    rafId = null
    displayed.value = toValue(target)
  }

  function restart() {
    if (reducedMotion.value || duration <= 0) return finish()
    if (rafId) cancelAnimationFrame(rafId)
    displayed.value = 0
    startedAt = performance.now()
    rafId = requestAnimationFrame(step)
  }

  onMounted(restart)
  watch(() => toValue(target), restart)
  watch(reducedMotion, reduced => {
    if (reduced && rafId) finish()
  })
  onBeforeUnmount(() => {
    if (rafId) cancelAnimationFrame(rafId)
  })

  return { displayed, restart }
}
