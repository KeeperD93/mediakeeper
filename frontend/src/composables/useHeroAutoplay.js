import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { usePrefersReducedMotion } from '@/composables/usePrefersReducedMotion'

export function useHeroAutoplay(sessionsRef, intervalMs = 10000) {
  // Read on mount before the autoplay starts below: its hook runs first.
  const reduceMotion = usePrefersReducedMotion()
  const idx = ref(0)
  const current = computed(() => sessionsRef.value[idx.value] || {})
  let timer = null

  function clearTimer() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function restart() {
    clearTimer()
    if (reduceMotion.value) return
    if (sessionsRef.value.length > 1) {
      timer = setInterval(() => {
        idx.value = (idx.value + 1) % sessionsRef.value.length
      }, intervalMs)
    }
  }

  function goTo(i) {
    idx.value = i
    restart()
  }

  watch(
    () => sessionsRef.value.length,
    () => {
      if (idx.value >= sessionsRef.value.length) idx.value = 0
      restart()
    },
  )
  // Sync: the timer follows each change at once, even one made before a pending flush.
  watch(reduceMotion, restart, { flush: 'sync' })

  onMounted(restart)
  onUnmounted(clearTimer)

  return { idx, current, goTo, restart }
}
