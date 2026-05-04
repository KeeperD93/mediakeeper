import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useRooms } from '@/composables/portal/useRooms'
import { EVENT_KIND } from '@/constants/events'
import { MEDIA_TYPE } from '@/constants/media'

export function useEventCreateModal(emit) {
  const { t } = useI18n()
  const { apiGet } = useApi()
  const { create, searchUsers } = useRooms()

  const kind = ref(EVENT_KIND.PRIVATE)
  const title = ref('')
  const date = ref('')
  const time = ref('')
  const comment = ref('')

  const mediaQuery = ref('')
  const mediaResults = ref([])
  const selectedMedia = ref([])

  const userQuery = ref('')
  const userResults = ref([])
  const selectedUsers = ref([])

  const error = ref('')
  const submitting = ref(false)

  const todayISO = computed(() => new Date().toISOString().slice(0, 10))

  let mediaTimer = null
  function onMediaInput() {
    clearTimeout(mediaTimer)
    mediaTimer = setTimeout(async () => {
      if (mediaQuery.value.trim().length < 2) {
        mediaResults.value = []
        return
      }
      try {
        const res = await apiGet(
          `/api/portal/catalog/search?q=${encodeURIComponent(mediaQuery.value)}&available_only=true`,
        )
        mediaResults.value = res?.items || []
      } catch {
        mediaResults.value = []
      }
    }, 250)
  }

  function addMedia(r) {
    if (
      selectedMedia.value.some(
        m => m.tmdb_id === (r.tmdb_id || r.id) && m.media_type === r.media_type,
      )
    )
      return
    if (selectedMedia.value.length >= 20) return
    selectedMedia.value.push({
      tmdb_id: r.tmdb_id || r.id,
      media_type: r.media_type || MEDIA_TYPE.MOVIE,
      title: r.title,
      poster_url: r.poster_url || r.poster || null,
      runtime_min: r.runtime || null,
    })
    mediaQuery.value = ''
    mediaResults.value = []
  }
  function removeMedia(i) {
    selectedMedia.value.splice(i, 1)
  }

  let dragIdx = null
  function onDragStart(i, e) {
    dragIdx = i
    e.dataTransfer.effectAllowed = 'move'
  }
  function onDrop(target) {
    if (dragIdx === null || dragIdx === target) return
    const arr = selectedMedia.value
    const moved = arr.splice(dragIdx, 1)[0]
    arr.splice(target, 0, moved)
    dragIdx = null
  }

  let userTimer = null
  function onUserInput() {
    clearTimeout(userTimer)
    userTimer = setTimeout(async () => {
      if (userQuery.value.trim().length < 1) {
        userResults.value = []
        return
      }
      userResults.value = await searchUsers(userQuery.value)
    }, 200)
  }
  function addUser(u) {
    if (selectedUsers.value.some(x => x.id === u.id)) return
    if (selectedUsers.value.length >= 19) return
    selectedUsers.value.push(u)
    userQuery.value = ''
    userResults.value = []
  }
  function removeUser(id) {
    selectedUsers.value = selectedUsers.value.filter(u => u.id !== id)
  }

  const canSubmit = computed(() => {
    if (!title.value.trim()) return false
    if (!selectedMedia.value.length) return false
    if (!date.value || !time.value) return false
    return true
  })

  async function submit() {
    if (!canSubmit.value) return
    error.value = ''
    submitting.value = true
    const scheduled = new Date(`${date.value}T${time.value}:00`)
    if (scheduled.getTime() <= Date.now()) {
      error.value = t('portal.mkEvents.create.errPast')
      submitting.value = false
      return
    }
    const payload = {
      title: title.value.trim(),
      kind: kind.value,
      tmdb_ids: selectedMedia.value,
      scheduled_at: scheduled.toISOString(),
      comment: comment.value.trim() || null,
      invitees: kind.value === EVENT_KIND.PRIVATE ? selectedUsers.value.map(u => u.id) : null,
    }
    try {
      const res = await create(payload)
      if (res?.error) {
        error.value = t(`portal.mkEvents.errors.${res.error}`, res.error)
        submitting.value = false
        return
      }
      emit('created', res)
      emit('close')
    } catch (e) {
      error.value = String(e?.message || e)
    } finally {
      submitting.value = false
    }
  }

  return {
    kind,
    title,
    date,
    time,
    comment,
    mediaQuery,
    mediaResults,
    selectedMedia,
    userQuery,
    userResults,
    selectedUsers,
    error,
    submitting,
    todayISO,
    canSubmit,
    onMediaInput,
    addMedia,
    removeMedia,
    onDragStart,
    onDrop,
    onUserInput,
    addUser,
    removeUser,
    submit,
  }
}
