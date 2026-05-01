import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useSubtitles } from '@/composables/useSubtitles'
import { useConfirm } from '@/composables/useConfirm'

/**
 * Per-episode subtitle/audio management used inside SubSeriesOverlay:
 * loads existing tracks, runs an OpenSubtitles search, downloads a
 * chosen result, deletes external subs and batch-removes embedded
 * streams. Extracted so the overlay template + state stay under 300
 * lines.
 */
export function useEpisodeSubDetail({ seriesNameRef, onDownloaded }) {
  const { t } = useI18n()
  const { apiGet, apiPost } = useApi()
  const { showToast } = useToast()
  const { defaultLanguagesParam, loadQuota, translateError } = useSubtitles()
  const mkConfirm = useConfirm()

  const selectedEp = ref(null)
  const epSubs = ref(null)
  const epAudio = ref([])
  const epFilePath = ref('')
  const epResults = ref([])
  const epSearching = ref(false)
  const downloading = ref(null)
  const lastDlResult = ref(null)
  const removing = ref(false)
  const removeSelection = ref([])
  const compareSelection = ref([])
  const showComparator = ref(false)

  function resetEpisode() {
    selectedEp.value = null
    epSubs.value = null
    epResults.value = []
  }

  function toggleCompareSelect(result) {
    const idx = compareSelection.value.findIndex(s => s.file_id === result.file_id)
    if (idx >= 0) {
      compareSelection.value.splice(idx, 1)
    } else {
      if (compareSelection.value.length >= 2) compareSelection.value.shift()
      compareSelection.value.push(result)
    }
  }

  watch(selectedEp, async (ep) => {
    if (!ep) return
    epSubs.value = null
    epAudio.value = []
    epResults.value = []
    epFilePath.value = ''
    lastDlResult.value = null
    removeSelection.value = []
    try {
      const d = await apiGet(`/api/subtitles/existing/${ep.item_id}`)
      if (d) {
        epSubs.value = d.streams || []
        epAudio.value = d.audio_streams || []
        epFilePath.value = d.file_path || ep.file_path || ''
      }
    } catch {
      epSubs.value = []
    }
  })

  async function searchEp() {
    if (!selectedEp.value) return
    const ep = selectedEp.value
    epSearching.value = true
    epResults.value = []
    try {
      const body = { query: seriesNameRef.value, languages: defaultLanguagesParam.value }
      if (ep.series_imdb_id) body.imdb_id = ep.series_imdb_id
      if (ep.season > 0) body.season = ep.season
      if (ep.episode > 0) body.episode = ep.episode
      if (epFilePath.value) body.file_path = epFilePath.value
      const d = await apiPost('/api/subtitles/search', body)
      if (d && d.results) epResults.value = d.results
      if (!epResults.value.length) showToast(t('common.noResults'), TOAST_TYPE.INFO)
    } catch { showToast(t('common.error'), TOAST_TYPE.ERR) }
    epSearching.value = false
  }

  async function downloadEp(result) {
    const ep = selectedEp.value
    const filePath = epFilePath.value || ep?.file_path
    if (!filePath || !ep) return
    const lang = result.language || 'fr'
    const map = { fr: 'fr', en: 'en', es: 'es', de: 'de', it: 'it', pt: 'pt' }
    const lc = map[lang] || lang
    const dot = filePath.lastIndexOf('.')
    const dest = dot > 0 ? filePath.substring(0, dot) + '.' + lc + '.srt' : filePath + '.' + lc + '.srt'

    downloading.value = result.file_id
    lastDlResult.value = null
    try {
      const d = await apiPost('/api/subtitles/download', {
        file_id: result.file_id, destination: dest, item_id: ep.item_id,
        media_name: `${seriesNameRef.value} — ${ep.name}`, media_type: 'Episode',
        series_name: seriesNameRef.value, season: ep.season || 0, episode: ep.episode || 0,
        subtitle_id: result.subtitle_id || '', file_name: result.file_name || '',
        language: result.language || '', quality_score: result.quality_score || 0,
        hash_match: result.hash_match || false, hearing_impaired: result.hearing_impaired || false,
        foreign_parts_only: result.foreign_parts_only || false, from_trusted: result.from_trusted || false,
        ai_translated: result.ai_translated || false,
      })
      if (d && d.success) {
        showToast(t('subtitles.downloaded'), TOAST_TYPE.OK)
        lastDlResult.value = d
        loadQuota()
        onDownloaded?.()
        const existing = await apiGet(`/api/subtitles/existing/${ep.item_id}`)
        if (existing) epSubs.value = existing.streams || []
      } else if (d && d.error) { showToast(translateError(d.error), TOAST_TYPE.ERR) }
    } catch { showToast(t('common.error'), TOAST_TYPE.ERR) }
    downloading.value = null
  }

  async function deleteSub(sub) {
    if (removing.value) return
    removing.value = true
    try {
      const d = await apiPost('/api/subtitles/delete', { path: sub.path })
      if (d && d.success) {
        showToast(t('common.success'), TOAST_TYPE.OK)
        epSubs.value = epSubs.value.filter(s => s.index !== sub.index)
      }
    } catch (e) { console.warn('[useEpisodeSubDetail.deleteSub] delete failed', e) }
    removing.value = false
  }

  function toggleRemove(index) {
    const i = removeSelection.value.indexOf(index)
    if (i >= 0) removeSelection.value.splice(i, 1)
    else removeSelection.value.push(index)
  }

  async function batchRemove() {
    if (removing.value || !removeSelection.value.length || !selectedEp.value) return
    const count = removeSelection.value.length
    const ok = await mkConfirm({
      title: t('common.confirmTitle.remove'),
      message: t('subtitles.removeBatchConfirm', { count }),
      variant: 'danger',
    })
    if (!ok) return
    removing.value = true
    showToast(t('subtitles.removingStream'), TOAST_TYPE.INFO)
    try {
      const d = await apiPost('/api/subtitles/remove-streams-batch', {
        item_id: selectedEp.value.item_id,
        stream_indices: removeSelection.value,
      })
      if (d && d.success) {
        showToast(t('subtitles.streamsRemoved', { count: d.removed_count }), TOAST_TYPE.OK)
        removeSelection.value = []
        const existing = await apiGet(`/api/subtitles/existing/${selectedEp.value.item_id}`)
        if (existing) {
          epSubs.value = existing.streams || []
          epAudio.value = existing.audio_streams || []
        }
      } else if (d && d.error) {
        showToast(translateError(d.error), TOAST_TYPE.ERR)
      }
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    removing.value = false
  }

  return {
    selectedEp, epSubs, epAudio, epFilePath, epResults, epSearching,
    downloading, lastDlResult, removing, removeSelection,
    compareSelection, showComparator,
    resetEpisode, toggleCompareSelect,
    searchEp, downloadEp, deleteSub, toggleRemove, batchRemove,
  }
}
