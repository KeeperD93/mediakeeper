/**
 * Whether the device asks for reduced motion, kept live: the ref follows the
 * setting when it changes while the page is open. False until mounted.
 */
import { onMounted, onUnmounted, ref } from 'vue'

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'

export function usePrefersReducedMotion() {
  const reduced = ref(false)
  let query = null
  const sync = event => {
    reduced.value = event.matches
  }

  onMounted(() => {
    // jsdom (unit tests) has no matchMedia.
    if (typeof window.matchMedia !== 'function') return
    query = window.matchMedia(REDUCED_MOTION_QUERY)
    reduced.value = query.matches
    query.addEventListener('change', sync)
  })
  onUnmounted(() => query?.removeEventListener('change', sync))

  return reduced
}
