import { ref, readonly, type DeepReadonly, type Ref } from 'vue'
import type { Router } from 'vue-router'
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
}

const toasts = ref<ToastItem[]>([])
let toastId = 0

const ROUTE_MODULES: Record<string, string> = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/stats': 'Statistics',
  '/media-manager': 'Manager',
  '/notifications': 'Notifications',
  '/logs': 'Logs',
  '/healthcheck': 'Health',
  '/watchlist': 'Tracking',
  '/duplicates': 'Duplicates',
  '/subtitles': 'Subtitles',
  '/settings': 'Settings',
  '/changelog': 'Changelog',
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
    const id = ++toastId
    const path = _routerInstance?.currentRoute?.value?.path || '/'
    const module = ROUTE_MODULES[path] || 'MediaKeeper'
    toasts.value.push({ id, message, type, meta, module })

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
