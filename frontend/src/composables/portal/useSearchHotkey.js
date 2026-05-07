import { onMounted, onUnmounted } from 'vue'

function isCmdK(event) {
  if (event.key !== 'k' && event.key !== 'K') return false
  return event.ctrlKey === true || event.metaKey === true
}

function isTextEntry(target) {
  if (!target) return false
  if (typeof target.isContentEditable === 'boolean' && target.isContentEditable) return true
  // Defensive fallback — some runtimes (e.g. jsdom in tests) don't reflect
  // the contenteditable attribute into the IDL property, so also probe it
  // directly so the shortcut still respects rich-text editors there.
  if (typeof target.getAttribute === 'function') {
    const attr = target.getAttribute('contenteditable')
    if (attr === '' || attr === 'true' || attr === 'plaintext-only') return true
  }
  const tag = (target.tagName || '').toUpperCase()
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

export function useSearchHotkey(focusSearch) {
  function handler(event) {
    if (!isCmdK(event)) return
    if (isTextEntry(event.target)) return
    event.preventDefault()
    if (typeof focusSearch === 'function') focusSearch()
  }

  onMounted(() => {
    document.addEventListener('keydown', handler)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handler)
  })
}
