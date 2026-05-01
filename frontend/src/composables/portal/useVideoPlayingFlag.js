/**
 * Reference-counted body flag for "a portal video is currently playing".
 *
 * Multiple components (HeroBanner, EmbyRecentHero, ...) can all need
 * the topbar's backdrop-filter dropped at the same time. A naive
 * "toggle this body class on/off" approach breaks as soon as two
 * sources fight: when one of them stops playing, it wipes the class
 * even though the other is still playing, and the blur snaps back.
 *
 * This composable keeps a module-level counter so the body class is
 * only removed once **every** holder has released their claim. Each
 * component grabs a release() function on mount and calls it on
 * unmount (or whenever its own video stops). The counter is purely
 * in-memory — no Vuex / pinia / event bus needed.
 */

let count = 0

function apply() {
  if (typeof document === 'undefined') return
  document.body.classList.toggle('mk-portal-video-playing', count > 0)
}

export function useVideoPlayingFlag() {
  let held = false

  function setPlaying(v) {
    if (v && !held) {
      count += 1
      held = true
      apply()
    } else if (!v && held) {
      count = Math.max(0, count - 1)
      held = false
      apply()
    }
  }

  // Always release on unmount, even if the caller forgot.
  function release() { setPlaying(false) }

  return { setPlaying, release }
}
