import { ref, computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi, resolveApiError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { FEEDBACK_PLATFORMS } from '@/constants/feedback'

const DESKTOP = 'desktop'
const MOBILE = 'mobile'
const BOTH = 'both'

// Stored platform slug <-> the two-checkbox set used in the edit form.
function platformToSet(p) {
  return p === DESKTOP || p === MOBILE ? [p] : [...FEEDBACK_PLATFORMS]
}
function setToPlatform(set) {
  const d = set.includes(DESKTOP)
  const m = set.includes(MOBILE)
  if (d && !m) return DESKTOP
  if (m && !d) return MOBILE
  return BOTH
}

/**
 * Feedback moderation queue: state + the load / edit / validate / reject actions.
 * Extracted from TrackerView so the view only presents; ``busyIds`` is
 * a per-report set — an action on one row never re-enables another row mid-flight.
 */
export function useFeedbackModeration() {
  const { t } = useI18n()
  const { apiGet, apiPatch, apiPost } = useApi()
  const { showToast } = useToast()

  const tab = ref('pending')
  const reports = ref([])
  const loading = ref(false)
  const editingId = ref(null)
  const form = ref(null)
  const busyIds = reactive(new Set())

  const canSave = computed(
    () => !!(form.value && form.value.title.trim() && form.value.description.trim()),
  )
  const isBusy = id => busyIds.has(id)

  async function load() {
    loading.value = true
    try {
      const data = await apiGet(`/api/feedback/reports?status=${tab.value}`)
      reports.value = data?.items ?? []
    } catch (e) {
      showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
    } finally {
      loading.value = false
    }
  }

  function switchTab(next) {
    if (tab.value === next) return
    tab.value = next
    editingId.value = null
    load()
  }

  function startEdit(r) {
    editingId.value = r.id
    form.value = {
      type: r.type,
      title: r.title,
      description: r.description,
      reproduction: r.reproduction || '',
      resolution: r.resolution || '',
      platforms: platformToSet(r.platform),
      tags: [...(r.tags || [])],
    }
  }

  function cancelEdit() {
    editingId.value = null
    form.value = null
  }

  function toggleIn(list, value) {
    const i = list.indexOf(value)
    if (i === -1) list.push(value)
    else list.splice(i, 1)
  }
  const togglePlatform = p => toggleIn(form.value.platforms, p)
  const toggleTag = tag => toggleIn(form.value.tags, tag)

  async function _run(id, action, okKey) {
    busyIds.add(id)
    try {
      await action()
      showToast(t(okKey), TOAST_TYPE.OK)
      return true
    } catch (e) {
      showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
      return false
    } finally {
      busyIds.delete(id)
    }
  }

  async function save() {
    if (!canSave.value) return
    const id = editingId.value
    const ok = await _run(
      id,
      () =>
        apiPatch(`/api/feedback/reports/${id}`, {
          type: form.value.type,
          title: form.value.title.trim(),
          description: form.value.description.trim(),
          reproduction: form.value.reproduction.trim(),
          resolution: form.value.resolution.trim(),
          platform: setToPlatform(form.value.platforms),
          tags: form.value.tags,
        }),
      'feedback.tracker.saved',
    )
    if (ok) {
      cancelEdit()
      await load()
    }
  }

  async function validate(r) {
    const ok = await _run(
      r.id,
      () => apiPost(`/api/feedback/reports/${r.id}/validate`),
      'feedback.tracker.validated',
    )
    if (ok) reports.value = reports.value.filter(x => x.id !== r.id)
  }

  async function reject(r) {
    const ok = await _run(
      r.id,
      () => apiPost(`/api/feedback/reports/${r.id}/reject`),
      'feedback.tracker.rejected',
    )
    if (ok) reports.value = reports.value.filter(x => x.id !== r.id)
  }

  return {
    tab,
    reports,
    loading,
    editingId,
    form,
    canSave,
    isBusy,
    load,
    switchTab,
    startEdit,
    cancelEdit,
    togglePlatform,
    toggleTag,
    save,
    validate,
    reject,
  }
}
