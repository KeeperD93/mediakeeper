import { resolveApiError } from './useApi'
import { useToast } from './useToast'
import { TOAST_TYPE } from '@/constants/toast'

// Calls started per loader, kept at module scope like the stats state they write:
// only the newest call applies its answer, so a slower older one (the previous
// period, a refresh started before an exclusion) cannot overwrite it.
const callCounts = {}

/**
 * The runner of the Statistics loaders. `run(name, options, task)` starts one call
 * of loader `name`: `task(latest)` fetches, then writes only while `latest()` holds.
 * Every failure is logged; the newest call's failure also runs `onFail` and, unless
 * `notify` is false, shows a toast.
 */
export function useStatsLoadRunner() {
  const { toasts, showToast } = useToast()

  // The General tab starts six loads at once: one toast when they all fail.
  function notifyLoadFailed(e) {
    const message = resolveApiError(e?.message, 'common.apiError.loadFailed')
    if (!toasts.value.some(toast => toast.message === message)) showToast(message, TOAST_TYPE.ERR)
  }

  return async function run(name, { loading = null, notify = true, onFail = null }, task) {
    const call = (callCounts[name] = (callCounts[name] || 0) + 1)
    const latest = () => callCounts[name] === call
    if (loading) loading.value = true
    try {
      await task(latest)
    } catch (e) {
      console.error(`[useStats.${name}]`, e)
      if (!latest()) return
      onFail?.()
      if (notify) notifyLoadFailed(e)
    } finally {
      if (loading && latest()) loading.value = false
    }
  }
}
