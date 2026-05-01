import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { STREAM_TYPE } from '@/constants/subtitles'
import { useSubtitles } from '@/composables/useSubtitles'
import { useConfirm } from '@/composables/useConfirm'

/**
 * Library-side stream search: find existing audio/subtitle tracks
 * across the user's Emby library, select a batch and remove them.
 * Lives here because it inflates SubSearchTab past the 300-line
 * threshold and has no overlap with the OpenSubtitles flow.
 */
export function useSubStreamSearch() {
  const { t } = useI18n()
  const { apiGet, apiPost } = useApi()
  const { showToast } = useToast()
  const { translateError } = useSubtitles()
  const mkConfirm = useConfirm()

  const streamQuery = ref('')
  const streamTypeFilter = ref('all')
  const streamResults = ref([])
  const streamTotal = ref(0)
  const streamSearching = ref(false)
  const streamSearched = ref(false)
  const selectedStreams = ref([])
  const batchRemoving = ref(false)
  let _streamOffset = 0

  async function doStreamSearch() {
    if (!streamQuery.value.trim()) return
    streamSearching.value = true
    streamResults.value = []; streamTotal.value = 0; selectedStreams.value = []; _streamOffset = 0
    streamSearched.value = true
    try {
      const params = new URLSearchParams({
        query: streamQuery.value.trim(),
        stream_type: streamTypeFilter.value,
        start: '0', limit: '50',
      })
      const d = await apiGet(`/api/subtitles/search-streams?${params}`)
      if (d) { streamResults.value = d.items || []; streamTotal.value = d.total || 0; _streamOffset = streamResults.value.length }
    } catch { showToast(t('common.error'), TOAST_TYPE.ERR) }
    streamSearching.value = false
  }

  async function loadMoreStreams() {
    streamSearching.value = true
    try {
      const params = new URLSearchParams({
        query: streamQuery.value.trim(),
        stream_type: streamTypeFilter.value,
        start: String(_streamOffset), limit: '50',
      })
      const d = await apiGet(`/api/subtitles/search-streams?${params}`)
      if (d && d.items) { streamResults.value.push(...d.items); _streamOffset += d.items.length }
    } catch { /* silent: stream search fetch */ }
    streamSearching.value = false
  }

  function isStreamSelected(itemId, index) {
    return selectedStreams.value.some(s => s.item_id === itemId && s.stream_index === index)
  }

  function toggleStreamSelect(itemId, index, item, stream) {
    const idx = selectedStreams.value.findIndex(s => s.item_id === itemId && s.stream_index === index)
    if (idx >= 0) selectedStreams.value.splice(idx, 1)
    else selectedStreams.value.push({ item_id: itemId, stream_index: index, name: item.name, stream })
  }

  const allSelected = computed(() =>
    streamResults.value.length > 0 &&
    streamResults.value.every(item => item.matching_streams.every(s => isStreamSelected(item.item_id, s.index))),
  )

  function toggleSelectAll() {
    if (allSelected.value) {
      selectedStreams.value = []
    } else {
      selectedStreams.value = []
      for (const item of streamResults.value) {
        for (const s of item.matching_streams) {
          selectedStreams.value.push({ item_id: item.item_id, stream_index: s.index, name: item.name, stream: s })
        }
      }
    }
  }

  async function removeSingleStream(itemId, index, stream) {
    const label = `${stream.type === STREAM_TYPE.AUDIO ? 'Audio' : 'Subtitle'} ${stream.language?.toUpperCase()} ${stream.title || ''}`
    const ok = await mkConfirm({
      title: t('common.confirmTitle.remove'),
      message: t('subtitles.removeStreamConfirm', { stream: label }),
      variant: 'danger',
    })
    if (!ok) return
    showToast(t('subtitles.removingStream'), TOAST_TYPE.INFO)
    try {
      const d = await apiPost('/api/subtitles/remove-stream', { item_id: itemId, stream_index: index })
      if (d && d.success) {
        showToast(t('subtitles.streamRemoved'), TOAST_TYPE.OK)
        // Drop the stream locally instead of re-running the full search.
        const item = streamResults.value.find(i => i.item_id === itemId)
        if (item) {
          item.matching_streams = item.matching_streams.filter(s => s.index !== index)
          if (!item.matching_streams.length) streamResults.value = streamResults.value.filter(i => i.item_id !== itemId)
        }
        selectedStreams.value = selectedStreams.value.filter(s => !(s.item_id === itemId && s.stream_index === index))
      } else if (d && d.error) showToast(translateError(d.error), TOAST_TYPE.ERR)
    } catch { showToast(t('common.error'), TOAST_TYPE.ERR) }
  }

  async function batchRemove() {
    const count = selectedStreams.value.length
    const confirmed = await mkConfirm({
      title: t('common.confirmTitle.remove'),
      message: t('subtitles.batchRemoveConfirm', { count }),
      variant: 'danger',
    })
    if (!confirmed) return
    batchRemoving.value = true
    showToast(t('subtitles.removingStream'), TOAST_TYPE.INFO)
    try {
      const d = await apiPost('/api/subtitles/batch-remove-streams', {
        operations: selectedStreams.value.map(s => ({ item_id: s.item_id, stream_index: s.stream_index })),
      })
      if (d) {
        const ok = d.success?.length || 0
        const fail = d.failed?.length || 0
        showToast(`${ok} ${t('subtitles.streamRemoved').toLowerCase()}${fail ? `, ${fail} ${t('common.error').toLowerCase()}` : ''}`, ok ? TOAST_TYPE.OK : TOAST_TYPE.ERR)
        const removed = new Set((d.success || []).map(s => `${s.item_id}:${s.stream_index}`))
        for (const item of streamResults.value) {
          item.matching_streams = item.matching_streams.filter(s => !removed.has(`${item.item_id}:${s.index}`))
        }
        streamResults.value = streamResults.value.filter(i => i.matching_streams.length > 0)
        selectedStreams.value = selectedStreams.value.filter(s => !removed.has(`${s.item_id}:${s.stream_index}`))
      }
    } catch { showToast(t('common.error'), TOAST_TYPE.ERR) }
    batchRemoving.value = false
  }

  return {
    streamQuery, streamTypeFilter, streamResults, streamTotal,
    streamSearching, streamSearched, selectedStreams, batchRemoving,
    allSelected,
    doStreamSearch, loadMoreStreams,
    isStreamSelected, toggleStreamSelect, toggleSelectAll,
    removeSingleStream, batchRemove,
  }
}
