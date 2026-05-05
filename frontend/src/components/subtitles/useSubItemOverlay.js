import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useSubtitles } from '@/composables/useSubtitles'
import { useConfirm } from '@/composables/useConfirm'

export function useSubItemOverlay(props, emit) {
  const { t } = useI18n()
  const { apiGet, apiPost } = useApi()
  const { showToast } = useToast()
  const { defaultLanguagesParam, loadQuota, translateError } = useSubtitles()
  const mkConfirm = useConfirm()

  const subs = ref(null)
  const audio = ref([])
  const filePath = ref('')
  const mediaDuration = ref(0)
  const results = ref([])
  const searching = ref(false)
  const downloading = ref(null)
  const lastDlResult = ref(null)
  const shiftMs = ref(0)
  const removing = ref(false)
  const removeSelection = ref([])
  const compareSelection = ref([])
  const showComparator = ref(false)

  function toggleCompareSelect(result) {
    const idx = compareSelection.value.findIndex(s => s.file_id === result.file_id)
    if (idx >= 0) {
      compareSelection.value.splice(idx, 1)
    } else {
      if (compareSelection.value.length >= 2) compareSelection.value.shift()
      compareSelection.value.push(result)
    }
  }

  async function loadDetails() {
    if (!props.item?.item_id) {
      subs.value = []
      return
    }
    subs.value = null
    audio.value = []
    results.value = []
    filePath.value = ''
    lastDlResult.value = null
    try {
      const d = await apiGet(`/api/subtitles/existing/${props.item.item_id}`)
      if (d) {
        subs.value = d.streams || []
        audio.value = d.audio_streams || []
        filePath.value = d.file_path || props.item.file_path || ''
        mediaDuration.value = d.media_duration_sec || 0
      } else {
        subs.value = []
      }
    } catch {
      subs.value = []
    }
  }

  async function searchItem() {
    if (!props.item) return
    searching.value = true
    results.value = []
    try {
      const body = {
        query: props.item.series_name || props.item.name,
        languages: defaultLanguagesParam.value,
      }
      if (props.item.type === 'Movie') {
        if (props.item.tmdb_id) body.tmdb_id = String(props.item.tmdb_id)
        if (props.item.imdb_id) body.imdb_id = props.item.imdb_id
      }
      if (props.item.type === 'Episode') {
        if (props.item.series_imdb_id) body.imdb_id = props.item.series_imdb_id
        if (props.item.season > 0) body.season = props.item.season
        if (props.item.episode > 0) body.episode = props.item.episode
      }
      if (filePath.value) body.file_path = filePath.value
      const d = await apiPost('/api/subtitles/search', body)
      if (d && d.results) results.value = d.results
      if (!results.value.length) showToast(t('common.noResults'), TOAST_TYPE.INFO)
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    searching.value = false
  }

  async function downloadItem(result) {
    const fp = filePath.value || props.item?.file_path
    if (!fp) return
    const lang = result.language || 'fr'
    const map = { fr: 'fr', en: 'en', es: 'es', de: 'de', it: 'it', pt: 'pt' }
    const lc = map[lang] || lang
    const dot = fp.lastIndexOf('.')
    const dest = dot > 0 ? fp.substring(0, dot) + '.' + lc + '.srt' : fp + '.' + lc + '.srt'

    downloading.value = result.file_id
    lastDlResult.value = null
    try {
      const d = await apiPost('/api/subtitles/download', {
        file_id: result.file_id,
        destination: dest,
        item_id: props.item.item_id,
        media_name: props.item.series_name
          ? `${props.item.series_name} — ${props.item.name}`
          : props.item.name,
        media_type: props.item.type,
        series_name: props.item.series_name || '',
        season: props.item.season || 0,
        episode: props.item.episode || 0,
        subtitle_id: result.subtitle_id || '',
        file_name: result.file_name || '',
        language: result.language || '',
        quality_score: result.quality_score || 0,
        hash_match: result.hash_match || false,
        hearing_impaired: result.hearing_impaired || false,
        foreign_parts_only: result.foreign_parts_only || false,
        from_trusted: result.from_trusted || false,
        ai_translated: result.ai_translated || false,
        media_duration_sec: mediaDuration.value,
      })
      if (d && d.success) {
        showToast(t('subtitles.downloaded'), TOAST_TYPE.OK)
        lastDlResult.value = d
        loadQuota()
        emit('downloaded')
        await loadDetails()
      } else if (d && d.error) {
        showToast(translateError(d.error), TOAST_TYPE.ERR)
      }
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    downloading.value = null
  }

  async function deleteSub(sub) {
    if (removing.value) return
    removing.value = true
    try {
      const d = await apiPost('/api/subtitles/delete', { path: sub.path })
      if (d && d.success) {
        showToast(t('common.success'), TOAST_TYPE.OK)
        subs.value = subs.value.filter(s => s.index !== sub.index)
      }
    } catch (e) {
      console.warn('[useSubItemOverlay.deleteSub] delete failed', e)
    }
    removing.value = false
  }

  function toggleRemove(index) {
    const i = removeSelection.value.indexOf(index)
    if (i >= 0) removeSelection.value.splice(i, 1)
    else removeSelection.value.push(index)
  }

  async function batchRemove() {
    if (removing.value || !removeSelection.value.length) return
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
        item_id: props.item.item_id,
        stream_indices: removeSelection.value,
      })
      if (d && d.success) {
        showToast(t('subtitles.streamsRemoved', { count: d.removed_count }), TOAST_TYPE.OK)
        removeSelection.value = []
        await loadDetails()
      } else if (d && d.error) {
        showToast(translateError(d.error), TOAST_TYPE.ERR)
      }
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    removing.value = false
  }

  async function doShift() {
    if (!shiftMs.value || !lastDlResult.value?.path) return
    try {
      const d = await apiPost('/api/subtitles/shift-srt', {
        path: lastDlResult.value.path,
        offset_ms: shiftMs.value,
      })
      if (d && d.success) {
        showToast(t('subtitles.shiftDone', { ms: shiftMs.value }), TOAST_TYPE.OK)
        shiftMs.value = 0
      } else if (d && d.error) showToast(translateError(d.error), TOAST_TYPE.ERR)
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
  }

  function formatChannels(ch) {
    if (ch === 1) return 'Mono'
    if (ch === 2) return 'Stereo'
    if (ch === 6) return '5.1'
    if (ch === 8) return '7.1'
    return `${ch}ch`
  }

  onMounted(() => {
    if (props.item) loadDetails()
  })

  return {
    subs,
    audio,
    results,
    searching,
    downloading,
    lastDlResult,
    shiftMs,
    removing,
    removeSelection,
    compareSelection,
    showComparator,
    toggleCompareSelect,
    searchItem,
    downloadItem,
    deleteSub,
    toggleRemove,
    batchRemove,
    doShift,
    formatChannels,
  }
}
