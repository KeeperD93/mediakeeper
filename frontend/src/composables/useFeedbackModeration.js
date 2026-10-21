import { ref, computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi, resolveApiError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { FEEDBACK_PLATFORMS, FEEDBACK_PLATFORM_BOTH, FEEDBACK_STATUS } from '@/constants/feedback'

// Stored platform slug <-> the two-chip set used in the edit form.
function platformToSet(p) {
  return FEEDBACK_PLATFORMS.includes(p) ? [p] : [...FEEDBACK_PLATFORMS]
}
function setToPlatform(set) {
  return set.length === 1 ? set[0] : FEEDBACK_PLATFORM_BOTH
}

/**
 * Feedback moderation queue: state + the load / edit / validate / reject actions.
 * Extracted from the moderation view so it only presents; ``busyIds`` is
 * a per-report set — an action on one row never re-enables another row mid-flight.
 */
export function useFeedbackModeration() {
  const { t } = useI18n()
  const { apiGet, apiPatch, apiPost } = useApi()
  const { showToast } = useToast()

  const tab = ref(FEEDBACK_STATUS.PENDING)
  const reports = ref([])
  const loading = ref(false)
  const loadFailed = ref(false)
  const editingId = ref(null)
  const form = ref(null)
  const busyIds = reactive(new Set())
  let loadSeq = 0

  const canSave = computed(
    () => !!(form.value && form.value.title.trim() && form.value.description.trim()),
  )
  const isBusy = id => busyIds.has(id)

  async function load() {
    // Only the latest load writes: a slower one from the previous tab must not
    // fill or clear the tab now on screen.
    const seq = ++loadSeq
    loading.value = true
    loadFailed.value = false
    try {
      const data = await apiGet(`/api/feedback/reports?status=${tab.value}`)
      if (seq === loadSeq) reports.value = data?.items ?? []
    } catch (e) {
      console.error('[useFeedbackModeration.load]', e)
      if (seq !== loadSeq) return
      reports.value = [] // no stale list or pending count beside the error
      loadFailed.value = true
      showToast(resolveApiError(e.message, 'common.apiError.loadFailed'), TOAST_TYPE.ERR)
    } finally {
      if (seq === loadSeq) loading.value = false
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

  // One call on report `id`; `name` labels its log, `failKey` names a failure
  // that has no message of its own (a lost connection, for one).
  async function _run(id, { name, call, okKey, failKey }) {
    busyIds.add(id)
    try {
      await call()
      showToast(t(okKey), TOAST_TYPE.OK)
      return true
    } catch (e) {
      console.error(`[useFeedbackModeration.${name}]`, e)
      showToast(resolveApiError(e.message, failKey), TOAST_TYPE.ERR)
      return false
    } finally {
      busyIds.delete(id)
    }
  }

  async function save() {
    if (!canSave.value) return
    const id = editingId.value
    const ok = await _run(id, {
      name: 'save',
      call: () =>
        apiPatch(`/api/feedback/reports/${id}`, {
          type: form.value.type,
          title: form.value.title.trim(),
          description: form.value.description.trim(),
          reproduction: form.value.reproduction.trim(),
          resolution: form.value.resolution.trim(),
          platform: setToPlatform(form.value.platforms),
          tags: form.value.tags,
        }),
      okKey: 'feedback.moderation.saved',
      failKey: 'common.apiError.saveFailed',
    })
    if (ok) {
      cancelEdit()
      await load()
    }
  }

  async function validate(r) {
    const ok = await _run(r.id, {
      name: 'validate',
      call: () => apiPost(`/api/feedback/reports/${r.id}/validate`),
      okKey: 'feedback.moderation.validated',
      failKey: 'common.apiError.submitFailed',
    })
    if (ok) reports.value = reports.value.filter(x => x.id !== r.id)
  }

  async function reject(r) {
    const ok = await _run(r.id, {
      name: 'reject',
      call: () => apiPost(`/api/feedback/reports/${r.id}/reject`),
      okKey: 'feedback.moderation.rejected',
      failKey: 'common.apiError.saveFailed',
    })
    if (ok) reports.value = reports.value.filter(x => x.id !== r.id)
  }

  return {
    tab,
    reports,
    loading,
    loadFailed,
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
