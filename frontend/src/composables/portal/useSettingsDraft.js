import { computed, reactive, ref } from 'vue'
import { useApi } from '@/composables/useApi'

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
  const saved = reactive({ ...DEFAULTS })
  const draft = reactive({ ...DEFAULTS })
  const loaded = ref(false)
  const loading = ref(false)
  const saving = ref(false)

  const dirtyKeys = computed(() => KEYS.filter(k => draft[k] !== saved[k]))
  const dirty = computed(() => dirtyKeys.value.length > 0)

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
    } finally {
      loading.value = false
    }
  }

  async function save() {
    if (!dirty.value) return
    saving.value = true
    try {
      const payload = Object.fromEntries(dirtyKeys.value.map(k => [k, draft[k]]))
      const res = await apiPatch(SETTINGS_URL, payload)
      // The service layer can snap/re-order some values (event capacity), so
      // re-seed the snapshot from the authoritative response.
      if (res) apply(res)
    } finally {
      saving.value = false
    }
  }

  function reset() {
    for (const k of KEYS) draft[k] = saved[k]
  }

  return { draft, saved, dirty, dirtyKeys, loaded, loading, saving, load, save, reset }
}
