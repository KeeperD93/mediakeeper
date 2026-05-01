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
 */
import { ref, readonly, type DeepReadonly, type Ref } from 'vue'

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

let resolver: ((value: boolean) => void) | null = null

const VARIANTS: readonly ConfirmVariant[] = ['danger', 'warn', 'info']

function open(opts: ConfirmOptions = {}): Promise<boolean> {
  // If a previous prompt is still open, resolve it as cancelled first.
  if (state.value.open && resolver) {
    resolver(false)
    resolver = null
  }

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

  return new Promise<boolean>(resolve => {
    resolver = resolve
  })
}

function close(result: boolean): void {
  if (resolver) {
    resolver(Boolean(result))
    resolver = null
  }
  state.value = { ...state.value, open: false }
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
    accept: () => close(true),
    cancel: () => close(false),
  }
}
