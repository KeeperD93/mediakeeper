/**
 * Roll-animation + Web Audio "slot machine" for the Surprise overlay.
 * Handles the 5s ease-out scan through the pool, the final landing tick,
 * and the sticky sound-on/off toggle. Extracted from SurpriseOverlay.vue
 * to keep the component under 300 lines.
 */
import { ref, onBeforeUnmount } from 'vue'

export function useSurpriseRoll({ getPool, onReveal }) {
  const rolling = ref(false)
  const activeIdx = ref(-1)
  // Sound toggle is sticky across sessions via localStorage.
  const soundOn = ref(localStorage.getItem('mk_surprise_sound') !== 'off')

  let audioCtx = null
  let tickCount = 0
  let rollTimeouts = []

  function toggleSound() {
    soundOn.value = !soundOn.value
    localStorage.setItem('mk_surprise_sound', soundOn.value ? 'on' : 'off')
  }

  function ensureCtx() {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
    if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => {})
    return audioCtx
  }

  // One short click per highlighted card. Frequency ticks up slightly on
  // each hit to give the draw a "slot machine" feel.
  function playTick() {
    if (!soundOn.value) return
    try {
      const ctx = ensureCtx()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'square'
      osc.frequency.value = 620 + Math.min(120, tickCount * 3)
      gain.gain.value = 0.0001
      gain.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + 0.005)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.08)
      osc.connect(gain).connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + 0.09)
      tickCount++
    } catch {
      /* audio blocked — silently ignore */
    }
  }

  function playFinal() {
    if (!soundOn.value) return
    try {
      const ctx = ensureCtx()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = 1320
      gain.gain.value = 0.0001
      gain.gain.exponentialRampToValueAtTime(0.28, ctx.currentTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.5)
      osc.connect(gain).connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + 0.55)
    } catch {
      /* ignore */
    }
  }

  function clearRollTimers() {
    rollTimeouts.forEach(clearTimeout)
    rollTimeouts = []
  }

  // Highlight a random cell at increasing intervals, easing out over 5s
  // before landing on the final pick. Calls onReveal(finalIdx) when done.
  function startRoll() {
    const pool = getPool()
    if (rolling.value || !pool.length) return
    clearRollTimers()
    rolling.value = true
    tickCount = 0

    const total = pool.length
    const TOTAL_MS = 5000
    const MIN_INTERVAL = 70
    const MAX_INTERVAL = 320
    let elapsed = 0
    let lastIdx = -1

    const ease = t => 1 - Math.pow(1 - t, 3)

    const step = () => {
      const t = elapsed / TOTAL_MS
      if (t >= 1) {
        const finalIdx = Math.floor(Math.random() * total)
        activeIdx.value = finalIdx
        playFinal()
        rollTimeouts.push(
          setTimeout(() => {
            rolling.value = false
            onReveal?.(finalIdx)
          }, 400),
        )
        return
      }
      let idx = Math.floor(Math.random() * total)
      if (idx === lastIdx && total > 1) idx = (idx + 1) % total
      lastIdx = idx
      activeIdx.value = idx
      playTick()
      const interval = MIN_INTERVAL + (MAX_INTERVAL - MIN_INTERVAL) * ease(t)
      elapsed += interval
      rollTimeouts.push(setTimeout(step, interval))
    }
    step()
  }

  function resetRoll() {
    clearRollTimers()
    activeIdx.value = -1
    rolling.value = false
  }

  onBeforeUnmount(clearRollTimers)

  return {
    rolling,
    activeIdx,
    soundOn,
    toggleSound,
    startRoll,
    resetRoll,
    clearRollTimers,
  }
}
