import { computed, onBeforeUnmount, ref } from 'vue'

/**
 * Cinema room — countdown, academy intro and now-time ticker. Pulled
 * out of ``CinemaRoomView.vue`` to keep the orchestrator under the
 * 300-line file size rule. The composable owns:
 *
 *   - ``now``                  : reactive ``Date.now()`` ticked every
 *     second.
 *   - ``remainingMs``,
 *     ``countdownNegative``,
 *     ``canLaunch``,
 *     ``countdownDisplay``    : derived from ``scheduledTime`` and the
 *     ticker.
 *   - ``academyActive``,
 *     ``academyValue``,
 *     ``academyDone``         : 10-second countdown overlay played
 *     once the room opens.
 *   - ``startTicker()``        : wire the 1 Hz interval (call from
 *     onMounted).
 *   - ``startAcademy()``,
 *     ``resetAcademy()``       : manage the countdown overlay.
 *
 * All intervals are auto-cleared on ``onBeforeUnmount``.
 */
export function useCinemaRoomFlow(scheduledTime) {
  const now = ref(Date.now())
  const academyActive = ref(false)
  const academyValue = ref(10)
  const academyDone = ref(false)

  let tickTimer = null
  let academyTimer = null

  const remainingMs = computed(() => scheduledTime.value - now.value)
  const countdownNegative = computed(() => remainingMs.value < 0)
  const canLaunch = computed(() => remainingMs.value <= 0)
  // The 10-second academy intro should land flush against ``scheduled_at``
  // so its final ``0`` lines up with the main countdown hitting zero.
  // Trigger it 10 s before the deadline rather than at deadline — see the
  // ``CinemaRoomView`` watcher below.
  const canStartAcademy = computed(() => remainingMs.value <= 10_000)

  const countdownDisplay = computed(() => {
    const ms = Math.abs(remainingMs.value)
    const total = Math.floor(ms / 1000)
    const h = Math.floor(total / 3600)
    const m = Math.floor((total % 3600) / 60)
    const s = total % 60
    if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  })

  function startTicker() {
    tickTimer = setInterval(() => {
      now.value = Date.now()
    }, 1000)
  }

  function startAcademy() {
    academyActive.value = true
    academyValue.value = 10
    academyTimer = setInterval(() => {
      academyValue.value -= 1
      if (academyValue.value <= 0) {
        clearInterval(academyTimer)
        academyTimer = null
        academyActive.value = false
        academyDone.value = true
      }
    }, 1000)
  }

  function resetAcademy() {
    academyDone.value = false
    academyActive.value = false
    startAcademy()
  }

  onBeforeUnmount(() => {
    if (tickTimer) clearInterval(tickTimer)
    if (academyTimer) clearInterval(academyTimer)
  })

  return {
    now,
    remainingMs,
    countdownNegative,
    canLaunch,
    canStartAcademy,
    countdownDisplay,
    academyActive,
    academyValue,
    academyDone,
    startTicker,
    startAcademy,
    resetAcademy,
  }
}
