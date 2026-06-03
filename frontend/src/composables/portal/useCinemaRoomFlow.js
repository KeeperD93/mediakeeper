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
 *     ``academyDone``         : 10-second countdown overlay played once
 *     the room opens — all derived from the same ``now`` ticker so the
 *     overlay stays in lock-step with the main countdown.
 *   - ``startTicker()``        : wire the 1 Hz interval (call from
 *     onMounted).
 *   - ``startAcademy()``,
 *     ``resetAcademy()``       : manage the countdown overlay.
 *
 * The single 1 Hz interval is auto-cleared on ``onBeforeUnmount``.
 */
export function useCinemaRoomFlow(scheduledTime) {
  const now = ref(Date.now())
  // Timestamp the academy intro counts down to (0 = idle). Both the
  // displayed value and the "ready" flip derive from ``now``, so the
  // overlay never drifts out of phase with the main countdown.
  const academyTarget = ref(0)
  const academyDone = ref(false)

  let tickTimer = null

  const remainingMs = computed(() => scheduledTime.value - now.value)
  const countdownNegative = computed(() => remainingMs.value < 0)
  const canLaunch = computed(() => remainingMs.value <= 0)
  // The 10-second academy intro should land flush against ``scheduled_at``
  // so its final second lines up with the main countdown hitting zero.
  // Trigger it 10 s before the deadline rather than at deadline, AND skip
  // it entirely once we are past T0 — a latecomer joining the room after
  // the screening started doesn't need to sit through a 10-second intro,
  // they should land straight on the launch CTA. The ``CinemaRoomView``
  // ``load()`` flow handles the post-T0 case via ``skipToReady()``.
  const canStartAcademy = computed(() => remainingMs.value <= 10_000 && remainingMs.value > 0)

  const countdownDisplay = computed(() => {
    const ms = Math.abs(remainingMs.value)
    // Count down with ceil so the timer reads 00:00 exactly at T0 (and the
    // academy intro, derived from the same ``now``, stays in sync); count
    // elapsed time up with floor.
    const total = remainingMs.value > 0 ? Math.ceil(ms / 1000) : Math.floor(ms / 1000)
    const h = Math.floor(total / 3600)
    const m = Math.floor((total % 3600) / 60)
    const s = total % 60
    if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  })

  // Academy overlay state, derived from ``now`` + ``academyTarget`` so it
  // shares the main countdown's tick and rounding (a separate interval
  // used to drift ~1 s out of phase).
  const academyActive = computed(
    () => academyTarget.value > 0 && !academyDone.value && now.value < academyTarget.value,
  )
  const academyValue = computed(() =>
    Math.max(1, Math.ceil((academyTarget.value - now.value) / 1000)),
  )

  function startTicker() {
    tickTimer = setInterval(() => {
      now.value = Date.now()
      // Flip to "ready" on the same tick that drives the visible
      // countdown, so the poster appears exactly when the intro hits 0.
      if (academyTarget.value > 0 && now.value >= academyTarget.value) {
        academyTarget.value = 0
        academyDone.value = true
      }
    }, 1000)
  }

  function startAcademy() {
    // Count the pre-show intro down to ``scheduled_at`` itself so the
    // overlay and the main countdown share one target and one ticker.
    // A latecomer between T-10s and T0 naturally gets the shorter intro.
    academyDone.value = false
    academyTarget.value = scheduledTime.value
  }

  function skipToReady() {
    // Latecomer joining after T0: there is nothing useful to count
    // down to — surface the launch CTA immediately.
    academyTarget.value = 0
    academyDone.value = true
  }

  function resetAcademy() {
    // Between-films replay: ``scheduled_at`` has passed, so run a fresh
    // 10 s intro counting from now.
    academyDone.value = false
    academyTarget.value = now.value + 10_000
  }

  onBeforeUnmount(() => {
    if (tickTimer) clearInterval(tickTimer)
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
    skipToReady,
    resetAcademy,
  }
}
