/**
 * useConfirm — singleton state-driven confirm dialog.
 *
 * Usage:
 *   const confirm = useConfirm()
 *   const ok = await confirm({
 *     title: t('common.confirm.deleteTitle'),
 *     message: t('common.confirm.deleteMessage'),
 *     variant: 'danger',          // 'danger' | 'warn' | 'info' (default 'info')
 *     confirmLabel: t('common.delete'),
 *     cancelLabel: t('common.cancel'),
 *   })
 *   if (!ok) return
 *
 * Mount <MkConfirmDialog /> once in App.vue for the state to be rendered.
 *
 * One prompt is on screen at a time: another one asked meanwhile waits its
 * turn instead of cancelling it (two rows of a list can both need an answer).
 * The same prompt asked again while it waits or shows (a double click) is
 * answered "no" at once, so its action runs once. A waiting prompt shows in
 * place of the one just answered: for a moment it cannot be accepted, so the
 * second click of a double click (or a repeated Enter) lands on nothing.
 */
import { nextTick, ref, readonly, type DeepReadonly, type Ref } from 'vue'

export type ConfirmVariant = 'danger' | 'warn' | 'info'

export interface ConfirmOptions {
  title?: string
  message?: string
  variant?: ConfirmVariant
  confirmLabel?: string
  cancelLabel?: string
}

interface ConfirmState {
  open: boolean
  title: string
  message: string
  variant: ConfirmVariant
  confirmLabel: string
  cancelLabel: string
}

// Module-scope singleton state (shared across all useConfirm() callers)
const state = ref<ConfirmState>({
  open: false,
  title: '',
  message: '',
  variant: 'info',
  confirmLabel: '',
  cancelLabel: '',
})

interface PendingConfirm {
  opts: ConfirmOptions
  resolve: (value: boolean) => void
}

// The prompt holding the dialog (shown, or about to be), and those waiting.
let current: PendingConfirm | null = null
const waiting: PendingConfirm[] = []

// Windows' default double-click time: an acceptance sooner than this after a
// waiting prompt appears was meant for the previous one.
export const QUEUED_PROMPT_GUARD_MS = 500
let acceptableFrom = 0

const VARIANTS: readonly ConfirmVariant[] = ['danger', 'warn', 'info']
const OPTION_KEYS = ['title', 'message', 'variant', 'confirmLabel', 'cancelLabel'] as const

const sameOptions = (a: ConfirmOptions, b: ConfirmOptions): boolean =>
  OPTION_KEYS.every(key => a[key] === b[key])

function render(opts: ConfirmOptions): void {
  const variant: ConfirmVariant =
    opts.variant && VARIANTS.includes(opts.variant) ? opts.variant : 'info'

  state.value = {
    open: true,
    title: opts.title || '',
    message: opts.message || '',
    variant,
    confirmLabel: opts.confirmLabel || '',
    cancelLabel: opts.cancelLabel || '',
  }
}

function open(opts: ConfirmOptions = {}): Promise<boolean> {
  if ([current, ...waiting].some(prompt => prompt && sameOptions(prompt.opts, opts))) {
    return Promise.resolve(false)
  }
  return new Promise<boolean>(resolve => {
    const prompt = { opts, resolve }
    if (current) {
      waiting.push(prompt)
    } else {
      current = prompt
      acceptableFrom = 0 // nothing was just answered in its place
      render(opts)
    }
  })
}

function close(result: boolean): void {
  const answered = current
  // Taken now, shown once the dialog has closed (focus back on Cancel): a
  // prompt asked by the answered caller queues behind it.
  const next = waiting.shift() ?? null
  current = next
  state.value = { ...state.value, open: false }
  answered?.resolve(Boolean(result))
  if (next) {
    nextTick(() => {
      if (current !== next) return
      render(next.opts)
      acceptableFrom = Date.now() + QUEUED_PROMPT_GUARD_MS
    })
  }
}

export function useConfirm(): (opts?: ConfirmOptions) => Promise<boolean> {
  return open
}

export interface ConfirmInternal {
  state: DeepReadonly<Ref<ConfirmState>>
  accept: () => void
  cancel: () => void
}

// Internal accessors for <MkConfirmDialog />. Not part of the public API.
export function _useConfirmState(): ConfirmInternal {
  return {
    state: readonly(state),
    accept: () => {
      if (Date.now() >= acceptableFrom) close(true)
    },
    cancel: () => close(false),
  }
}
