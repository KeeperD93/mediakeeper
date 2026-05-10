import { ref, shallowRef } from 'vue'
import { useApi } from './useApi'
import { useToast } from './useToast'

export const { apiGet, apiFetch, apiPut, apiPost } = useApi()
export const { showToast } = useToast()

// _t is a mutable late-binding reference to vue-i18n's `t()`.
// Set by the `useMediaManager()` facade once a component binds it.
// Using a getter ensures all importing modules read the current value.
let _tImpl = k => k
export const _t = (...args) => _tImpl(...args)
export function setT(t) {
  _tImpl = t
}

// ─── DYNAMIC CATEGORIES ───
export const CATS = ref([])
export const catsLoaded = ref(false)

// ─── REGEX analyseur ───
export const NAMING_PATTERNS = {
  resolution: /\b(480p|720p|1080p|2160p|4K|UHD)\b/i,
  codec: /\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|VP9|AV1)\b/i,
  year: /\b(19|20)\d{2}\b/,
  episode: /[Ss]\d{1,2}[Ee]\d{1,2}|\d{1,2}x\d{2}/,
}

export const GENRE_CAT_MAP = {
  16: { label: 'Animation', color: '#f59e0b', cat: 'filmsdanimation' },
  99: { label: 'Documentary', color: '#06b6d4', cat: 'documentaires' },
  10402: { label: 'Show', color: '#ec4899', cat: 'spectacles' },
}

// ─── GLOBAL STATE ───
export const activeCat = ref('telechargement')
export const subPath = ref('')
export const files = shallowRef([])
export const filtered = shallowRef([])
export const checked = ref(new Set())
export const loading = ref(false)
export const filterQuery = ref('')
export const sortMode = ref('name-asc')
export const expandedMode = ref(false)
export const savedFiltered = ref(null)
export const savedChecked = ref(null)
export const tags = ref({})

// TMDB
export const searchType = ref('movie')
export const tmdbResults = ref([])
export const tmdbYearQuery = ref('')
export const selectedTmdb = ref(null)
export const currentSeason = ref(null)
export const seasons = ref([])
export const showSeasonPanel = ref(false)

// Tooltip
export const tooltip = ref({
  visible: false,
  title: '',
  year: '',
  vote: '',
  overview: '',
  x: 0,
  y: 0,
})

// Colonne right
export const newNames = ref([])
export const renaming = ref(false)
export const dragSrc = ref(null)
export const progress = ref(0)

// Modals
export const modalConfirm = ref({ show: false, lines: [] })
export const modalFolders = ref({ show: false })
export const modalMoveSrc = ref(null)
export const modalMoveShow = ref(false)
export const modalRenameFolderShow = ref(false)
export const renameFolderCurrent = ref('')
export const renameFolderValue = ref('')

// Modal folders
export const folderSeriesName = ref('')
export const folderAudioTags = ref(new Set())
export const folderBatchAudioTags = ref(new Set())
export const folderSeasonTags = ref([])
export const folderPreview = ref('')
export const folderExistingDirs = ref([])

// Modal move
export const moveCat = ref('telechargement')
export const movePath = ref('')
export const moveFolders = ref([])
export const moveSearchQ = ref('')
export const moveSelectedPath = ref(null)
export const moveLoading = ref(false)
export const moveManualPath = ref('')

// Drag cross-category
export const dragFileIdx = ref(null)
export const dragIsGrouped = ref(false)
export const dragOverCat = ref(null)

// ─── HISTORIQUE RENAME + UNDO (localStorage, TTL 7 jours) ───
export const _HIST_TTL = 7 * 24 * 60 * 60 * 1000
export const renameHistory = ref([])
try {
  const raw = JSON.parse(localStorage.getItem('mk_rename_history') || '[]')
  renameHistory.value = raw.filter(e => Date.now() - e.timestamp < _HIST_TTL).slice(0, 50)
  localStorage.setItem('mk_rename_history', JSON.stringify(renameHistory.value))
} catch {
  renameHistory.value = []
}
export function _saveRenameHistory() {
  try {
    localStorage.setItem('mk_rename_history', JSON.stringify(renameHistory.value.slice(0, 50)))
  } catch {
    /* silent: localStorage quota/privacy mode */
  }
}

// ─── HISTORIQUE MOVE ───
export const moveHistory = ref([])
try {
  moveHistory.value = JSON.parse(localStorage.getItem('mk_move_history') || '[]')
    .filter(e => Date.now() - e.timestamp < _HIST_TTL)
    .slice(0, 30)
} catch {
  moveHistory.value = []
}
export function _saveMoveHistory() {
  try {
    localStorage.setItem('mk_move_history', JSON.stringify(moveHistory.value.slice(0, 30)))
  } catch {
    /* silent: localStorage quota/privacy mode */
  }
}
export const showMoveHistoryModal = ref(false)

// ─── CONFIGURABLE ANOMALY RULES ───
export const DEFAULT_ANOMALY_RULES = {
  checkResolution: true,
  checkYear: true,
  checkDoubleSpaces: true,
  checkMultipleUnderscores: true,
  checkNameLength: true,
  maxNameLength: 200,
  checkDotsCount: true,
  maxDots: 3,
}
function _loadAnomalyRules() {
  try {
    return {
      ...DEFAULT_ANOMALY_RULES,
      ...JSON.parse(localStorage.getItem('mk_anomaly_rules') || '{}'),
    }
  } catch {
    return { ...DEFAULT_ANOMALY_RULES }
  }
}
export const anomalyRules = ref(_loadAnomalyRules())
export const showAnomalyConfigModal = ref(false)

// Analyse nommage
export const namingIssues = ref({})
export const analysisActive = ref(false)

// Multi-categorys
export const multiCatMode = ref(false)

// Progression par file
export const fileRenameStatus = ref({})

// Conflits move
export const moveConflicts = ref([])
export const showMoveConflictModal = ref(false)
export const pendingMoveFiles = ref([])
export const pendingMoveDest = ref('')

// Thumbnails cache
export const thumbnailCache = ref({})

// Threshold new file (24h)
export const newFileThresholdMs = 24 * 60 * 60 * 1000

// ─── PROFILS DE RENOMMAGE ───
export const DEFAULT_PROFILES = [
  {
    id: 'default-fr',
    name: 'FR Standard',
    builtin: true,
    config: { movie: '{t} ({y})', tv: '{n} - {s00e00} - {t}', lang: 'fr-FR' },
  },
  {
    id: 'default-vostfr',
    name: 'VOSTFR',
    builtin: true,
    config: { movie: '{t} ({y})', tv: '{n} - {s00e00} - {t} VOSTFR', lang: 'fr-FR' },
  },
  {
    id: 'default-en',
    name: 'EN Original',
    builtin: true,
    config: { movie: '{t} ({y})', tv: '{n} - {s00e00} - {t}', lang: 'en-US' },
  },
]
export const renameProfiles = ref([])
try {
  renameProfiles.value = JSON.parse(localStorage.getItem('mk_rename_profiles') || '[]')
} catch {
  renameProfiles.value = []
}
export function _saveProfiles() {
  try {
    localStorage.setItem('mk_rename_profiles', JSON.stringify(renameProfiles.value))
  } catch {
    /* silent: localStorage quota/privacy mode */
  }
}

// ─── CUSTOM RENAME RULES ───
export const customRules = ref([])
try {
  customRules.value = JSON.parse(localStorage.getItem('mk_custom_rules') || '[]')
} catch {
  customRules.value = []
}
export function _saveCustomRules() {
  try {
    localStorage.setItem('mk_custom_rules', JSON.stringify(customRules.value))
  } catch {
    /* silent: localStorage quota/privacy mode */
  }
}

// ─── RELEASE TAGS (admin-editable, persisted server-side) ───
export const releaseTags = ref([])
export const releaseTagsDefaults = ref([])
export const releaseTagsLoaded = ref(false)

// ─── ADVANCED FEATURES MODAL ───
export const showAdvancedModal = ref(false)
export const advancedTab = ref('profiles')
export const crossCatDuplicates = ref([])
export const checkingDuplicates = ref(false)

// Log d'errors de renaming
export const renameErrors = ref([])
export const showRenameErrorsModal = ref(false)

// Extraction running state
export const extractionRunning = ref(false)
export let extractionCancelled = false
export function setExtractionCancelled(v) {
  extractionCancelled = v
}

// Metadata file
export const fileMetaModal = ref({
  show: false,
  file: null,
  loading: false,
  data: null,
  parsed: null,
})

// Audio tags
export const _ALL_AUDIO_TAGS = [
  'MULTI',
  'VOSTFR',
  'VOSTA',
  'VFF',
  'VFI',
  'VO',
  'VF',
  'VF2',
  'DUBBED',
  'SUB',
  'OV',
  'VOSE',
  'CAST',
  'DUBLADO',
  'LEG',
  'RAW',
]

// Auto-search state
export const _autoSearchState = { timer: null, tmdbQueryEl: null, dirChangePending: false }

// ─── PROGRESSION ───
let _progressTimer = null
export function setProgress(pct) {
  progress.value = pct
}
export function endProgress() {
  progress.value = 100
  _progressTimer = setTimeout(() => {
    progress.value = 0
  }, 700)
}
