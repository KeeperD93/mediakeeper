import { ref, readonly, type DeepReadonly, type Ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'
import type { ToastType } from '@/constants/toast'

export interface ToastMeta {
  thumb?: string
  user?: string
  subtitle?: string
  [key: string]: unknown
}

export interface ToastItem {
  id: number
  message: string
  type: ToastType | string
  meta: ToastMeta | null
  module: string
  persistent: boolean
  // Auto-dismiss delay in ms, also the length of the countdown bar.
  duration: number
}

const toasts = ref<ToastItem[]>([])
let toastId = 0

// The header is an i18n key, resolved with t() in the toast renderer.
const GENERIC_MODULE = 'toastModule.app'

// An admin page (child of the '/' shell) heads its toasts with its own title, so a
// new page needs no extra entry; portal and sign-in pages keep the generic header.
function moduleKey(route: RouteLocationNormalizedLoaded | undefined): string {
  const titleKey = route?.meta.titleKey
  return route?.matched[0]?.path === '/' && typeof titleKey === 'string' ? titleKey : GENERIC_MODULE
}

let _routerInstance: Router | null = null

export interface UseToastApi {
  toasts: DeepReadonly<Ref<ToastItem[]>>
  showToast: (
    message: string,
    type?: ToastType | string,
    duration?: number,
    meta?: ToastMeta | null,
  ) => void
  removeToast: (id: number) => void
}

export function useToast(): UseToastApi {
  /**
   * Show a toast notification.
   * @param message  Main text
   * @param type     'ok' | 'err' | 'warn' | 'media' | 'info'
   * @param duration Auto-dismiss ms (0 = manual)
   * @param meta     Optional rich data: { thumb, user, subtitle }
   */
  function showToast(
    message: string,
    type: ToastType | string = 'ok',
    duration = 5000,
    meta: ToastMeta | null = null,
  ): void {
    // Nothing to say: the failure was already reported (a rate limit's own toast).
    if (!message) return
    const id = ++toastId
    const module = moduleKey(_routerInstance?.currentRoute.value)
    toasts.value.push({ id, message, type, meta, module, persistent: duration <= 0, duration })

    if (duration > 0) {
      setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id)
      }, duration)
    }
  }

  function removeToast(id: number): void {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return {
    toasts: readonly(toasts),
    showToast,
    removeToast,
  }
}

export function setToastRouter(router: Router): void {
  _routerInstance = router
}
