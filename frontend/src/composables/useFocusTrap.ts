import { watch, nextTick, onBeforeUnmount, type Ref } from 'vue'

export interface UseFocusTrapOptions {
  active: Ref<boolean>
  containerRef: Ref<HTMLElement | null>
  onEscape?: () => void
  initialFocusRef?: Ref<HTMLElement | null>
  returnFocusOnDeactivate?: boolean
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
  '[contenteditable="true"]',
].join(',')

function isVisible(el: HTMLElement): boolean {
  if (el.hidden) return false
  const win = el.ownerDocument.defaultView
  if (!win) return true
  const style = win.getComputedStyle(el)
  return style.display !== 'none' && style.visibility !== 'hidden'
}

function getFocusables(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(isVisible)
}

export function useFocusTrap(options: UseFocusTrapOptions): void {
  if (typeof document === 'undefined') return

  const returnFocus = options.returnFocusOnDeactivate ?? true
  let previouslyFocused: HTMLElement | null = null
  let listenerAttached = false

  function onKeydown(event: KeyboardEvent): void {
    const container = options.containerRef.value
    if (!container) return
    if (
      event.key === 'Escape' &&
      !event.altKey &&
      !event.ctrlKey &&
      !event.metaKey &&
      !event.shiftKey
    ) {
      event.preventDefault()
      options.onEscape?.()
      return
    }
    if (event.key !== 'Tab') return
    const focusables = getFocusables(container)
    if (focusables.length === 0) {
      event.preventDefault()
      container.focus()
      return
    }
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    const current = document.activeElement as HTMLElement | null
    // The container itself (its initial focus without initialFocusRef, or a
    // click on the panel's text) counts as the start of the cycle.
    if (event.shiftKey && (current === first || current === container)) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && current === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function attach(): void {
    if (listenerAttached) return
    document.addEventListener('keydown', onKeydown, true)
    listenerAttached = true
  }

  function detach(): void {
    if (!listenerAttached) return
    document.removeEventListener('keydown', onKeydown, true)
    listenerAttached = false
  }

  function activate(): void {
    previouslyFocused = (document.activeElement as HTMLElement | null) ?? null
    attach()
    void nextTick(() => {
      if (!options.active.value) return
      const container = options.containerRef.value
      // Focusable but out of the Tab order: a click on the panel's text then
      // lands on the panel, not on <body>, so Shift+Tab still wraps.
      if (container && !container.hasAttribute('tabindex')) container.tabIndex = -1
      const target = options.initialFocusRef?.value ?? container
      target?.focus?.()
    })
  }

  function deactivate(): void {
    detach()
    if (!returnFocus) {
      previouslyFocused = null
      return
    }
    const target = previouslyFocused
    previouslyFocused = null
    if (!target || !target.isConnected) return
    void nextTick(() => target.focus?.())
  }

  watch(
    () => options.active.value,
    (isActive, wasActive) => {
      if (isActive && !wasActive) activate()
      else if (!isActive && wasActive) deactivate()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    if (listenerAttached) deactivate()
  })
}
