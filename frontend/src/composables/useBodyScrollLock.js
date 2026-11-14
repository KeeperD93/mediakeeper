/**
 * Lock the page behind a window while `active` is true. Windows share one count:
 * when one hands over to the next (the first-login wizard, then the daily digest),
 * the page stays locked until the last one closes, whatever order they change in.
 */
import { onScopeDispose, watch } from 'vue'

let holders = 0
let previousOverflow = ''

function hold() {
  if (holders === 0) {
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  holders += 1
}

function release() {
  holders -= 1
  if (holders === 0) document.body.style.overflow = previousOverflow
}

export function useBodyScrollLock(active) {
  let holding = false
  const sync = on => {
    if (on === holding) return
    holding = on
    if (on) hold()
    else release()
  }
  watch(() => !!active.value, sync, { immediate: true })
  onScopeDispose(() => sync(false))
}
