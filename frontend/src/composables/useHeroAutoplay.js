import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'

export function useHeroAutoplay(sessionsRef, intervalMs = 10000) {
  const idx = ref(0)
  const current = computed(() => sessionsRef.value[idx.value] || {})
  let timer = null
  let mediaQuery = null
  const reduceMotion = ref(false)

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

  function onMotionChange(event) {
    reduceMotion.value = event.matches
    restart()
  }

  watch(
    () => sessionsRef.value.length,
    () => {
      if (idx.value >= sessionsRef.value.length) idx.value = 0
      restart()
    },
  )

  onMounted(() => {
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      mediaQuery = window.matchMedia(REDUCED_MOTION_QUERY)
      reduceMotion.value = mediaQuery.matches
      if (typeof mediaQuery.addEventListener === 'function') {
        mediaQuery.addEventListener('change', onMotionChange)
      } else if (typeof mediaQuery.addListener === 'function') {
        mediaQuery.addListener(onMotionChange)
      }
    }
    restart()
  })

  onUnmounted(() => {
    clearTimer()
    if (mediaQuery) {
      if (typeof mediaQuery.removeEventListener === 'function') {
        mediaQuery.removeEventListener('change', onMotionChange)
      } else if (typeof mediaQuery.removeListener === 'function') {
        mediaQuery.removeListener(onMotionChange)
      }
      mediaQuery = null
    }
  })

  return { idx, current, goTo, restart }
}
