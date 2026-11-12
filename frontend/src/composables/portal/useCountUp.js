/**
 * Animate a counter from 0 to ``target`` over ``duration`` ms using a
 * requestAnimationFrame loop, and again each time ``target`` changes when it
 * is a ref. Honors ``prefers-reduced-motion`` by snapping straight to the
 * final value.
 *
 * Surfaces a Vue ref ``displayed`` that components can render with
 * ``localizedNumber()`` to feed the hero billboard / live stats bar
 * count-up effect.
 */
import { onBeforeUnmount, onMounted, ref, toValue, watch } from 'vue'

const EASING = {
  easeOutQuart: t => 1 - Math.pow(1 - t, 4),
  linear: t => t,
}

function reducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function useCountUp(target, { duration = 1200, easing = 'easeOutQuart' } = {}) {
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

  function restart() {
    if (rafId) cancelAnimationFrame(rafId)
    if (reducedMotion() || duration <= 0) {
      displayed.value = toValue(target)
      return
    }
    displayed.value = 0
    startedAt = performance.now()
    rafId = requestAnimationFrame(step)
  }

  onMounted(restart)
  watch(() => toValue(target), restart)
  onBeforeUnmount(() => {
    if (rafId) cancelAnimationFrame(rafId)
  })

  return { displayed, restart }
}
