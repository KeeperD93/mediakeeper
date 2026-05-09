import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

export function useHeroAutoplay(sessionsRef, intervalMs = 10000) {
  const idx = ref(0)
  const current = computed(() => sessionsRef.value[idx.value] || {})
  let timer = null

  function restart() {
    if (timer) clearInterval(timer)
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

  onMounted(restart)
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return { idx, current, goTo, restart }
}
