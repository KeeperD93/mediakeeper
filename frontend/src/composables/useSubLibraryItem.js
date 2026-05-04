import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { STREAM_TYPE } from '@/constants/subtitles'
import { useSubtitles } from '@/composables/useSubtitles'
import { useConfirm } from '@/composables/useConfirm'

export function useSubLibraryItem(state) {
  const { t } = useI18n()
  const { apiGet, apiPost } = useApi()
  const { showToast } = useToast()
  const { defaultLanguagesParam, loadQuota, translateError } = useSubtitles()
  const mkConfirm = useConfirm()

  const {
    expandedId,
    itemSubs,
    itemAudio,
    itemFilePath,
    itemResults,
    itemSearching,
    downloading,
    lastDownloadResult,
  } = state

  async function toggleExpand(item) {
    if (expandedId.value === item.item_id) {
      expandedId.value = null
      return
    }
    expandedId.value = item.item_id
    itemSubs.value = null
    itemAudio.value = []
    itemResults.value = []
    itemFilePath.value = ''
    lastDownloadResult.value = null
    try {
      const d = await apiGet(`/api/subtitles/existing/${item.item_id}`)
      if (d) {
        itemSubs.value = d.streams || []
        itemAudio.value = d.audio_streams || []
        itemFilePath.value = d.file_path || item.file_path || ''
      }
    } catch {
      itemSubs.value = []
    }
  }

  async function searchForItem(item) {
    itemSearching.value = true
    itemResults.value = []
    try {
      const body = { query: item.series_name || item.name, languages: defaultLanguagesParam.value }
      if (item.type === 'Movie') {
        if (item.tmdb_id) body.tmdb_id = String(item.tmdb_id)
        if (item.imdb_id) body.imdb_id = item.imdb_id
      }
      if (item.type === 'Episode') {
        if (item.series_imdb_id) body.imdb_id = item.series_imdb_id
        if (item.season > 0) body.season = item.season
        if (item.episode > 0) body.episode = item.episode
      }
      if (itemFilePath.value) body.file_path = itemFilePath.value
      const d = await apiPost('/api/subtitles/search', body)
      if (d && d.results) itemResults.value = d.results
      if (!itemResults.value.length) showToast(t('common.noResults'), TOAST_TYPE.INFO)
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    itemSearching.value = false
  }

  async function downloadForItem(result, item) {
    const filePath = itemFilePath.value || item.file_path
    if (!filePath) return
    const lang = result.language || 'fr'
    const map = { fr: 'fr', en: 'en', es: 'es', de: 'de', it: 'it', pt: 'pt' }
    const lc = map[lang] || lang
    const dot = filePath.lastIndexOf('.')
    const dest =
      dot > 0 ? filePath.substring(0, dot) + '.' + lc + '.srt' : filePath + '.' + lc + '.srt'

    downloading.value = result.file_id
    lastDownloadResult.value = null
    try {
      const d = await apiPost('/api/subtitles/download', {
        file_id: result.file_id,
        destination: dest,
        item_id: item.item_id,
        media_name: item.series_name ? `${item.series_name} — ${item.name}` : item.name,
        media_type: item.type,
        series_name: item.series_name || '',
        season: item.season || 0,
        episode: item.episode || 0,
        subtitle_id: result.subtitle_id || '',
        file_name: result.file_name || '',
        language: result.language || '',
        quality_score: result.quality_score || 0,
        hash_match: result.hash_match || false,
        hearing_impaired: result.hearing_impaired || false,
        foreign_parts_only: result.foreign_parts_only || false,
        from_trusted: result.from_trusted || false,
        ai_translated: result.ai_translated || false,
        media_duration_sec: item.runtime_sec || 0,
      })
      if (d && d.success) {
        showToast(t('subtitles.downloaded'), TOAST_TYPE.OK)
        lastDownloadResult.value = d
        loadQuota()
        const existing = await apiGet(`/api/subtitles/existing/${item.item_id}`)
        if (existing) itemSubs.value = existing.streams || []
      } else if (d && d.error) {
        showToast(translateError(d.error), TOAST_TYPE.ERR)
      }
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    downloading.value = null
  }

  async function deleteSubtitle(sub) {
    try {
      const d = await apiPost('/api/subtitles/delete', { path: sub.path })
      if (d && d.success) {
        showToast(t('common.success'), TOAST_TYPE.OK)
        itemSubs.value = itemSubs.value.filter(s => s.index !== sub.index)
      }
    } catch (e) {
      console.warn('[useSubLibraryItem.deleteSubtitle] delete failed', e)
    }
  }

  async function removeStream({ item_id, stream_index, type, language }) {
    const label = `${type === STREAM_TYPE.AUDIO ? 'Audio' : 'Subtitle'} ${language.toUpperCase()}`
    const ok = await mkConfirm({
      title: t('common.confirmTitle.remove'),
      message: t('subtitles.removeStreamConfirm', { stream: label }),
      variant: 'danger',
    })
    if (!ok) return
    try {
      showToast(t('subtitles.removingStream'), TOAST_TYPE.INFO)
      const d = await apiPost('/api/subtitles/remove-stream', { item_id, stream_index })
      if (d && d.success) {
        showToast(t('subtitles.streamRemoved'), TOAST_TYPE.OK)
        const existing = await apiGet(`/api/subtitles/existing/${item_id}`)
        if (existing) {
          itemSubs.value = existing.streams || []
          itemAudio.value = existing.audio_streams || []
        }
      } else if (d && d.error) {
        showToast(translateError(d.error), TOAST_TYPE.ERR)
      }
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
  }

  return { toggleExpand, searchForItem, downloadForItem, deleteSubtitle, removeStream }
}
