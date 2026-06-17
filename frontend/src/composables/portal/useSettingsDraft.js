import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const SETTINGS_URL = '/api/portal/admin/settings'

// Keys from the generic /settings endpoint currently driven by the global
// draft + save bar, with type-correct defaults so the controls bind to valid
// values before the initial GET resolves (no undefined-prop flash). Mirrors
// the backend registry defaults. Extended as more categories migrate off their
// own per-card Save buttons (donation.*, quota.auto.* in later phases).
const DEFAULTS = {
  anonymize_requests: false,
  allow_adult_requests: false,
  'requests.auto_cleanup_days': 0,
  hero_trend_count: 10,
  'events.max_participants_min': 5,
  'events.max_participants_max': 20,
  default_language: '',
}
const KEYS = Object.keys(DEFAULTS)

// Free numeric inputs that can be emptied to '' by v-model.number. Their value
// must stay an integer in range, else the PATCH would ship '' and the backend
// rejects it (422). Selects and toggles cannot become invalid, so are not listed.
const NUMERIC_BOUNDS = {
  hero_trend_count: [0, 20],
  'requests.auto_cleanup_days': [0, 365],
}
const isValidInt = (v, [lo, hi]) => Number.isInteger(v) && v >= lo && v <= hi

/**
 * Central settings draft for the portal admin Configuration screen.
 *
 * Holds a working copy of every managed key, tracks which ones differ from
 * the last-saved snapshot, and PATCHes only the changed keys on save — so the
 * sticky save bar can offer a single, consistent "unsaved changes" model
 * across categories instead of per-card Save buttons.
 */
export function useSettingsDraft() {
  const { apiGet, apiPatch } = useApi()
  const { t } = useI18n()
  const { showToast } = useToast()
  const saved = reactive({ ...DEFAULTS })
  const draft = reactive({ ...DEFAULTS })
  const loaded = ref(false)
  const loading = ref(false)
  const saving = ref(false)

  const dirtyKeys = computed(() => KEYS.filter(k => draft[k] !== saved[k]))
  const dirty = computed(() => dirtyKeys.value.length > 0)
  // Keys whose value is out of range (e.g. an emptied number field). Blocks save
  // so an invalid value never ships as '' and gets silently rejected (422).
  const invalidKeys = computed(() =>
    KEYS.filter(k => k in NUMERIC_BOUNDS && !isValidInt(draft[k], NUMERIC_BOUNDS[k])),
  )
  const invalid = computed(() => invalidKeys.value.length > 0)

  function apply(res) {
    for (const k of KEYS) {
      saved[k] = res[k]
      draft[k] = res[k]
    }
  }

  async function load() {
    loading.value = true
    try {
      const res = await apiGet(SETTINGS_URL)
      if (res) {
        apply(res)
        loaded.value = true
      }
    } catch (e) {
      console.error('[useSettingsDraft.load]', e)
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
    } finally {
      loading.value = false
    }
  }

  async function save() {
    if (!dirty.value || invalid.value) return
    saving.value = true
    try {
      const payload = Object.fromEntries(dirtyKeys.value.map(k => [k, draft[k]]))
      const res = await apiPatch(SETTINGS_URL, payload)
      // The service layer can snap/re-order some values (event capacity), so
      // re-seed the snapshot from the authoritative response.
      if (res) apply(res)
    } catch (e) {
      console.error('[useSettingsDraft.save]', e)
      showToast(t('common.networkError'), TOAST_TYPE.ERR)
    } finally {
      saving.value = false
    }
  }

  function reset() {
    for (const k of KEYS) draft[k] = saved[k]
  }

  return { draft, saved, dirty, dirtyKeys, invalid, loaded, loading, saving, load, save, reset }
}
