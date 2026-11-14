/**
 * Plays the help demos: which demo, which view, paused or not. The views loop on a
 * timer; with « reduce motion » nothing moves and the viewer steps through them.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { usePrefersReducedMotion } from '@/composables/usePrefersReducedMotion'
import { DEMO, DEMO_TIMING } from '@/constants/portalWizardHelp'

export function useDemoPlayer() {
  const demo = ref(DEMO.REQUEST)
  const frame = ref(0)
  const paused = ref(false)
  const still = usePrefersReducedMotion()

  const views = computed(() => DEMO_TIMING[demo.value].views)
  const frameMs = computed(() => DEMO_TIMING[demo.value].ms)

  let timer = null
  let startedAt = 0
  let remaining = 0

  function stop() {
    clearTimeout(timer)
    timer = null
  }

  // Shows the current view for `ms`, then the next one, and so on.
  function run(ms) {
    stop()
    remaining = ms
    startedAt = Date.now()
    timer = setTimeout(() => {
      frame.value = (frame.value + 1) % views.value
      run(frameMs.value)
    }, ms)
  }

  function restart() {
    if (still.value || paused.value) stop()
    else run(frameMs.value)
  }

  function pick(id) {
    demo.value = id
    frame.value = 0
    paused.value = false
    restart()
  }

  // The CSS animations pause in the same tick, so the view resumes where it stopped.
  function togglePause() {
    if (paused.value) {
      paused.value = false
      run(remaining > 0 ? remaining : frameMs.value)
    } else {
      paused.value = true
      remaining -= Date.now() - startedAt
      stop()
    }
  }

  function step(delta) {
    frame.value = (frame.value + delta + views.value) % views.value
  }

  watch(still, restart)
  restart()
  onBeforeUnmount(stop)

  return { demo, frame, paused, still, views, frameMs, pick, togglePause, step }
}
