import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useTimezoneChoice } from '@/composables/useTimezoneChoice'
import { useToast } from '@/composables/useToast'
import { ONBOARDING_STEP as STEP } from '@/constants/onboarding'
import { TOAST_TYPE } from '@/constants/toast'

export function useOnboarding(emit) {
  const { t } = useI18n()
  const { apiGet, apiFetch } = useApi()
  const { showToast } = useToast()
  const timezone = useTimezoneChoice()

  const visible = ref(false)
  const currentStep = ref(0)
  const saving = ref(false)
  const tourActive = ref(0)

  const steps = computed(() => [
    { id: STEP.WELCOME, label: t('onboarding.stepWelcome') },
    { id: STEP.LOCALE, label: t('onboarding.stepLocale') },
    { id: STEP.EMBY, label: 'Emby' },
    { id: STEP.TMDB, label: 'TMDB' },
    { id: STEP.OPENSUBTITLES, label: 'OpenSubtitles' },
    { id: STEP.FOLDERS, label: t('onboarding.stepFolders') },
    { id: STEP.TOUR, label: t('onboarding.stepTour') },
    { id: STEP.DONE, label: t('onboarding.stepDone') },
  ])
  const currentStepId = computed(() => steps.value[currentStep.value].id)
  const zoneSaved = computed(() => Boolean(timezone.savedRow.value))

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
      if (!(await saveCurrentStep())) return
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

  /** False keeps the wizard on the step: the change was refused, or its failure already shown. */
  async function saveTimezone() {
    if (!timezone.canSave.value) return true
    // The warning is about changing a saved zone: a first choice on a new install needs none.
    if (timezone.savedRow.value && !(await timezone.confirmChoice())) return false
    return timezone.saveChoice()
  }

  async function saveCurrentStep() {
    saving.value = true
    try {
      const step = currentStepId.value
      if (step === STEP.LOCALE) return await saveTimezone()
      if (step === STEP.EMBY && emby.value.url && (emby.value.api_key || emby.value._configured)) {
        await apiFetch('/api/settings/tools/emby', {
          method: 'POST',
          body: JSON.stringify(buildToolPayload(emby.value, { url: emby.value.url })),
        })
        emby.value._configured = true
      }
      if (step === STEP.TMDB && (tmdb.value.api_key || tmdb.value._configured)) {
        await apiFetch('/api/settings/tools/tmdb', {
          method: 'POST',
          body: JSON.stringify(buildToolPayload(tmdb.value)),
        })
        tmdb.value._configured = true
      }
      if (step === STEP.OPENSUBTITLES && (openSubs.value.api_key || openSubs.value._configured)) {
        await apiFetch('/api/settings/tools/opensubtitles', {
          method: 'POST',
          body: JSON.stringify(buildToolPayload(openSubs.value)),
        })
        openSubs.value._configured = true
      }
      if (step === STEP.FOLDERS && hasFolders.value) {
        const payload = folders.value
          .filter(f => f.path.trim())
          .map(f => ({ key: f.key, label: f.label, path: f.path.trim() }))
        await apiFetch('/api/settings/media-folders', {
          method: 'PUT',
          body: JSON.stringify({ folders: payload }),
        })
      }
      return true
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

      const status = await apiGet('/api/onboarding/status')
      if (status?.authenticated && !status?.onboarding_done) {
        await timezone.loadChoice()
        visible.value = true
      }
    } catch {
      /* silent: onboarding check is best-effort, modal stays hidden */
    }
  }

  onMounted(checkAndShow)

  return {
    visible,
    currentStep,
    currentStepId,
    saving,
    tourActive,
    steps,
    zoneRows: timezone.rows,
    zoneKey: timezone.selectedKey,
    zoneRow: timezone.selectedRow,
    zoneSaved,
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
