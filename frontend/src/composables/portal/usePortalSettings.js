/**
 * usePortalSettings — orchestrates the premium settings page state.
 *
 * Responsibilities:
 * - Snapshot the profile into a flat editable form.
 * - Track which fields are dirty + provide reset / save.
 * - Debounce live username availability checks against the backend.
 * - Surface backend errors (display_name_locked / display_name_taken)
 *   as i18n-translated toasts at the consumer level.
 *
 * The composable exports a per-instance state factory (no module-scope
 * sharing) — different mounts of /portal/settings should not bleed
 * dirty state into each other.
 */
import { computed, reactive, ref, watch } from 'vue'

import { useApi } from '@/composables/useApi'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'

const FIELDS = [
  'display_name', 'bio', 'language', 'hide_adult', 'is_public',
  'selected_title', 'avatar_effect', 'favorite_genres',
]

function snapshot(profile) {
  if (!profile) return {}
  return {
    display_name: profile.display_name || '',
    bio: profile.bio || '',
    language: profile.language || 'fr',
    hide_adult: profile.hide_adult !== false,
    is_public: profile.is_public !== false,
    selected_title: profile.selected_title || null,
    avatar_effect: profile.avatar_effect || null,
    favorite_genres: Array.isArray(profile.favorite_genres)
      ? [...profile.favorite_genres]
      : [],
  }
}

function deepEqual(a, b) {
  if (a === b) return true
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false
    return a.every((v, i) => v === b[i])
  }
  return false
}

export function usePortalSettings() {
  const { profile, updateProfile } = usePortalAuth()
  const { apiGet, apiDelete, apiFetch } = useApi()

  const form = reactive(snapshot(profile.value))
  let pristine = snapshot(profile.value)

  const saving = ref(false)
  const lastSaveError = ref(null)

  const usernameState = reactive({
    must_set: false,
    locked: false,
    locked_until: null,
    lock_days: 180,
    current: '',
  })
  const usernameCheck = reactive({
    pending: false,
    available: null,   // null=unknown, true/false otherwise
    reason: null,      // 'free' | 'taken' | 'locked' | 'current' | 'invalid'
    suggestions: [],
  })

  watch(profile, (next) => {
    if (!next) return
    Object.assign(form, snapshot(next))
    pristine = snapshot(next)
  })

  const dirty = computed(() => {
    for (const k of FIELDS) {
      if (!deepEqual(form[k], pristine[k])) return true
    }
    return false
  })

  function discard() {
    Object.assign(form, pristine)
    lastSaveError.value = null
  }

  function buildPayload() {
    const payload = {}
    for (const k of FIELDS) {
      if (!deepEqual(form[k], pristine[k])) payload[k] = form[k]
    }
    return payload
  }

  async function save() {
    if (!dirty.value || saving.value) return { ok: true, skipped: true }
    saving.value = true
    lastSaveError.value = null
    try {
      const payload = buildPayload()
      const updated = await updateProfile(payload)
      if (updated) pristine = snapshot(updated)
      return { ok: true, profile: updated }
    } catch (err) {
      const detail = err?.data?.detail || err?.message || 'unknown'
      lastSaveError.value = detail
      return { ok: false, error: detail }
    } finally {
      saving.value = false
    }
  }

  let usernameTimer = null
  const USERNAME_DEBOUNCE_MS = 350

  async function fetchUsernameState() {
    try {
      const res = await apiGet('/api/portal/profiles/me/username-state')
      if (res) Object.assign(usernameState, res)
    } catch {
      // Non-blocking; the page still renders without the cooldown badge.
    }
  }

  function checkUsername(candidate) {
    if (usernameTimer) clearTimeout(usernameTimer)
    const trimmed = (candidate || '').trim()
    if (!trimmed) {
      usernameCheck.pending = false
      usernameCheck.available = null
      usernameCheck.reason = null
      usernameCheck.suggestions = []
      return
    }
    usernameCheck.pending = true
    usernameTimer = setTimeout(async () => {
      try {
        const res = await apiGet(
          `/api/portal/profiles/me/check-username?name=${encodeURIComponent(trimmed)}`,
        )
        usernameCheck.available = !!res?.available
        usernameCheck.reason = res?.reason || null
        usernameCheck.suggestions = res?.suggestions || []
      } catch {
        usernameCheck.available = null
        usernameCheck.reason = 'error'
        usernameCheck.suggestions = []
      } finally {
        usernameCheck.pending = false
      }
    }, USERNAME_DEBOUNCE_MS)
  }

  async function uploadAvatar(file) {
    const data = new FormData()
    data.append('file', file)
    // ``apiFetch`` detects FormData and skips the JSON Content-Type header,
    // letting the browser set the correct multipart boundary.
    const res = await apiFetch('/api/portal/profiles/me/avatar', {
      method: 'POST',
      body: data,
    })
    return res ? await res.json() : null
  }

  async function deleteCustomAvatar() {
    return apiDelete('/api/portal/profiles/me/avatar')
  }

  return {
    form,
    dirty,
    saving,
    lastSaveError,
    usernameState,
    usernameCheck,
    fetchUsernameState,
    checkUsername,
    save,
    discard,
    uploadAvatar,
    deleteCustomAvatar,
  }
}
