import { ref, computed, markRaw, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import {
  BarChart3,
  Bell,
  Captions,
  ClipboardCheck,
  Copy,
  Film,
  Home,
  ShieldCheck,
} from 'lucide-vue-next'

const ICONS = {
  dashboard: markRaw(Home),
  stats: markRaw(BarChart3),
  watchlist: markRaw(ClipboardCheck),
  media: markRaw(Film),
  duplicates: markRaw(Copy),
  health: markRaw(ShieldCheck),
  subtitles: markRaw(Captions),
  notifications: markRaw(Bell),
}

export function useOnboarding(props, emit) {
  const { t } = useI18n()
  const { apiGet, apiFetch } = useApi()
  const { showToast } = useToast()

  const visible = ref(false)
  const currentStep = ref(0)
  const saving = ref(false)
  const tourActive = ref(0)

  const steps = computed(() => [
    { id: 'welcome', label: t('onboarding.stepWelcome') },
    { id: 'emby', label: 'Emby' },
    { id: 'tmdb', label: 'TMDB' },
    { id: 'opensubtitles', label: 'OpenSubtitles' },
    { id: 'folders', label: t('onboarding.stepFolders') },
    { id: 'tour', label: t('onboarding.stepTour') },
    { id: 'done', label: t('onboarding.stepDone') },
  ])

  const features = computed(() => [
    {
      id: 'dash',
      bg: 'rgba(99,102,241,.12)',
      name: t('sidebar.dashboard'),
      desc: t('onboarding.modDashboard'),
      icon: ICONS.dashboard,
    },
    {
      id: 'stats',
      bg: 'rgba(16,185,129,.1)',
      name: t('sidebar.statistics'),
      desc: t('onboarding.modStats'),
      icon: ICONS.stats,
    },
    {
      id: 'wl',
      bg: 'rgba(139,92,246,.12)',
      name: t('sidebar.watchlist'),
      desc: t('onboarding.modWatchlist'),
      icon: ICONS.watchlist,
    },
    {
      id: 'media',
      bg: 'rgba(6,182,212,.1)',
      name: t('sidebar.mediaManager'),
      desc: t('onboarding.modMedia'),
      icon: ICONS.media,
    },
    {
      id: 'doub',
      bg: 'rgba(245,158,11,.1)',
      name: t('sidebar.duplicates'),
      desc: t('onboarding.modDoublons'),
      icon: ICONS.duplicates,
    },
    {
      id: 'health',
      bg: 'rgba(234,179,8,.1)',
      name: t('sidebar.healthCheck'),
      desc: t('onboarding.modHealth'),
      icon: ICONS.health,
    },
    {
      id: 'subs',
      bg: 'rgba(168,85,247,.1)',
      name: t('sidebar.subtitles'),
      desc: t('onboarding.modSubtitles'),
      icon: ICONS.subtitles,
    },
    {
      id: 'notif',
      bg: 'rgba(244,63,94,.1)',
      name: t('sidebar.notifications'),
      desc: t('onboarding.modNotifs'),
      icon: ICONS.notifications,
    },
  ])

  const modules = computed(() => [
    {
      id: 'dashboard',
      name: t('sidebar.dashboard'),
      bg: 'rgba(99,102,241,.12)',
      desc: t('onboarding.modDashboard'),
      icon: ICONS.dashboard,
      features: [
        t('onboarding.featSessions'),
        t('onboarding.featStats'),
        t('onboarding.featAlerts'),
        t('onboarding.featWidgets'),
      ],
    },
    {
      id: 'stats',
      name: t('sidebar.statistics'),
      bg: 'rgba(16,185,129,.1)',
      desc: t('onboarding.modStats'),
      icon: ICONS.stats,
      features: [
        t('onboarding.featHistory'),
        t('onboarding.featTopUsers'),
        t('onboarding.featLibraries'),
        t('onboarding.featHeatmap'),
      ],
    },
    {
      id: 'watchlist',
      name: t('sidebar.watchlist'),
      bg: 'rgba(139,92,246,.12)',
      desc: t('onboarding.modWatchlist'),
      icon: ICONS.watchlist,
      features: [
        t('onboarding.featMissing'),
        t('onboarding.featCalendar'),
        t('onboarding.featTimeline'),
        t('onboarding.featTracking'),
      ],
    },
    {
      id: 'media',
      name: t('sidebar.mediaManager'),
      bg: 'rgba(6,182,212,.1)',
      desc: t('onboarding.modMedia'),
      icon: ICONS.media,
      features: [
        t('onboarding.featTmdbRename'),
        t('onboarding.featBatchRename'),
        t('onboarding.featMove'),
        t('onboarding.featFolders'),
      ],
    },
    {
      id: 'duplicates',
      name: t('sidebar.duplicates'),
      bg: 'rgba(245,158,11,.1)',
      desc: t('onboarding.modDoublons'),
      icon: ICONS.duplicates,
      features: [
        t('onboarding.featDetect'),
        t('onboarding.featCompare'),
        t('onboarding.featAutoClean'),
        t('onboarding.featIgnore'),
      ],
    },
    {
      id: 'health',
      name: t('sidebar.healthCheck'),
      bg: 'rgba(234,179,8,.1)',
      desc: t('onboarding.modHealth'),
      icon: ICONS.health,
      features: [
        t('onboarding.featHealthCodecs'),
        t('onboarding.featHealthResolution'),
        t('onboarding.featHealthSubtitles'),
        t('onboarding.featHealthRules'),
      ],
    },
    {
      id: 'subtitles',
      name: t('sidebar.subtitles'),
      bg: 'rgba(168,85,247,.1)',
      desc: t('onboarding.modSubtitles'),
      icon: ICONS.subtitles,
      features: [
        t('onboarding.featSubSearch'),
        t('onboarding.featSubProfiles'),
        t('onboarding.featSubAuto'),
        t('onboarding.featSubAudit'),
      ],
    },
    {
      id: 'notifs',
      name: t('sidebar.notifications'),
      bg: 'rgba(244,63,94,.1)',
      desc: t('onboarding.modNotifs'),
      icon: ICONS.notifications,
      features: [
        t('onboarding.featDiscord'),
        t('onboarding.featDnd'),
        t('onboarding.featTemplates'),
        t('onboarding.featFilters'),
      ],
    },
  ])

  const emby = ref({
    url: '',
    api_key: '',
    api_key_length: 0,
    _testing: false,
    _status: null,
    _configured: false,
  })
  const tmdb = ref({
    api_key: '',
    api_key_length: 0,
    _testing: false,
    _status: null,
    _configured: false,
  })
  const openSubs = ref({
    api_key: '',
    api_key_length: 0,
    _testing: false,
    _status: null,
    _configured: false,
  })

  function buildToolPayload(model, extra = {}) {
    const payload = { enabled: true, ...extra }
    if (model.api_key) payload.api_key = model.api_key
    return payload
  }

  async function _testTool(obj, endpoint, body) {
    obj.value._testing = true
    obj.value._status = null
    try {
      await apiFetch(`/api/settings/tools/${endpoint}`, {
        method: 'POST',
        body: JSON.stringify(body),
      })
      const res = await apiGet(`/api/settings/tools/${endpoint}/ping`)
      obj.value._status = res?.online
        ? { type: 'ok', msg: t('onboarding.testOk') }
        : { type: 'err', msg: t('onboarding.testFail') }
    } catch {
      obj.value._status = { type: 'err', msg: t('common.networkError') }
    }
    obj.value._testing = false
  }

  const testEmby = () =>
    _testTool(emby, 'emby', buildToolPayload(emby.value, { url: emby.value.url }))
  const testTmdb = () => _testTool(tmdb, 'tmdb', buildToolPayload(tmdb.value))
  const testOpenSubs = () => _testTool(openSubs, 'opensubtitles', buildToolPayload(openSubs.value))

  let _folderId = 0
  // Folders start empty: every deployment mounts a different set of host
  // paths into the container (see docker-compose.prod.yml), so a hard-coded
  // list of English labels (Downloads, Movies, …) would either pollute the
  // payload with bogus entries on a fresh install or surface labels that
  // do not match the operator's actual layout. The wizard exposes an
  // "Add folder" button to declare exactly the paths the operator mounted.
  const folders = ref([])
  const hasFolders = computed(() => folders.value.some(f => f.path.trim()))
  const browsePath = ref('/')
  const browseDirs = ref([])
  const browseLoading = ref(false)
  const browseOpen = ref(null)

  async function loadBrowseDirs(path) {
    browseLoading.value = true
    try {
      const res = await apiGet(`/api/media/browse-dirs?path=${encodeURIComponent(path)}`)
      browseDirs.value = res?.dirs || []
    } catch {
      browseDirs.value = []
    }
    browseLoading.value = false
  }

  function openBrowser(folderId) {
    browseOpen.value = browseOpen.value === folderId ? null : folderId
    browsePath.value = '/'
    loadBrowseDirs('/')
  }

  function browseTo(path) {
    const normalized = '/' + path.replace(/^\/+/, '').replace(/\/+$/, '')
    browsePath.value = normalized
    loadBrowseDirs(normalized)
  }

  function selectBrowsePath(folderIndex, dirPath) {
    folders.value[folderIndex].path = dirPath
    browseOpen.value = null
  }

  function hydrateFolders(savedFolders = []) {
    if (!Array.isArray(savedFolders) || !savedFolders.length) return
    folders.value = savedFolders.map(folder => ({
      key: folder.key || `folder_${++_folderId}`,
      label: folder.label || '',
      path: folder.path || '',
      default: folder.path || '/media/...',
      _id: ++_folderId,
    }))
  }

  function addFolder() {
    folders.value.push({
      key: 'MEDIA_CUSTOM_' + _folderId,
      label: '',
      path: '',
      default: '/media/...',
      _id: ++_folderId,
    })
  }
  function removeFolder(i) {
    folders.value.splice(i, 1)
  }

  async function next() {
    if (saving.value) return
    try {
      await saveCurrentStep()
    } catch (e) {
      console.error('[useOnboarding.next] failed to save current step', e)
      showToast(t('common.apiError.saveFailed'), TOAST_TYPE.ERR)
      return
    }
    if (currentStep.value < steps.value.length - 1) currentStep.value++
  }
  function prev() {
    if (currentStep.value > 0) currentStep.value--
  }
  function skip() {
    currentStep.value++
  }

  async function saveCurrentStep() {
    saving.value = true
    try {
      if (
        currentStep.value === 1 &&
        emby.value.url &&
        (emby.value.api_key || emby.value._configured)
      ) {
        await apiFetch('/api/settings/tools/emby', {
          method: 'POST',
          body: JSON.stringify(buildToolPayload(emby.value, { url: emby.value.url })),
        })
        emby.value._configured = true
      }
      if (currentStep.value === 2 && (tmdb.value.api_key || tmdb.value._configured)) {
        await apiFetch('/api/settings/tools/tmdb', {
          method: 'POST',
          body: JSON.stringify(buildToolPayload(tmdb.value)),
        })
        tmdb.value._configured = true
      }
      if (currentStep.value === 3 && (openSubs.value.api_key || openSubs.value._configured)) {
        await apiFetch('/api/settings/tools/opensubtitles', {
          method: 'POST',
          body: JSON.stringify(buildToolPayload(openSubs.value)),
        })
        openSubs.value._configured = true
      }
      if (currentStep.value === 4 && hasFolders.value) {
        const payload = folders.value
          .filter(f => f.path.trim())
          .map(f => ({ key: f.key, label: f.label, path: f.path.trim() }))
        await apiFetch('/api/settings/media-folders', {
          method: 'PUT',
          body: JSON.stringify({ folders: payload }),
        })
      }
    } finally {
      saving.value = false
    }
  }

  async function complete() {
    saving.value = true
    try {
      await apiFetch('/api/onboarding/complete', { method: 'POST' })
      visible.value = false
      emit('done')
      showToast(t('onboarding.completeToast'), TOAST_TYPE.OK)
    } catch (e) {
      console.error('[useOnboarding.complete] failed to finalize onboarding', e)
      showToast(t('common.apiError.submitFailed'), TOAST_TYPE.ERR)
    } finally {
      saving.value = false
    }
  }

  async function checkAndShow() {
    try {
      const tools = await apiGet('/api/settings/tools').catch(() => ({}))
      if (tools?.emby?.url) emby.value.url = tools.emby.url
      emby.value._configured = !!(tools?.emby?.api_key_configured || tools?.emby?.api_key)
      emby.value.api_key_length = Number(tools?.emby?.api_key_length) || 0
      tmdb.value._configured = !!(tools?.tmdb?.api_key_configured || tools?.tmdb?.api_key)
      tmdb.value.api_key_length = Number(tools?.tmdb?.api_key_length) || 0
      openSubs.value._configured = !!(
        tools?.opensubtitles?.api_key_configured || tools?.opensubtitles?.api_key
      )
      openSubs.value.api_key_length = Number(tools?.opensubtitles?.api_key_length) || 0

      const savedFolders = await apiGet('/api/settings/media-folders').catch(() => [])
      hydrateFolders(savedFolders)

      if (props.forceShow) {
        visible.value = true
        return
      }

      const status = await apiGet('/api/onboarding/status')
      if (status?.authenticated && !status?.onboarding_done) visible.value = true
    } catch {
      /* silent: onboarding check is best-effort, modal stays hidden */
    }
  }

  onMounted(checkAndShow)

  return {
    visible,
    currentStep,
    saving,
    tourActive,
    steps,
    features,
    modules,
    emby,
    tmdb,
    openSubs,
    testEmby,
    testTmdb,
    testOpenSubs,
    folders,
    hasFolders,
    addFolder,
    removeFolder,
    browsePath,
    browseDirs,
    browseLoading,
    browseOpen,
    openBrowser,
    browseTo,
    selectBrowsePath,
    next,
    prev,
    skip,
    complete,
    checkAndShow,
  }
}
