import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { RULE_TYPE } from '@/constants/mediaManager'
import { useMediaManager } from '@/composables/useMediaManager'

/**
 * Shared handlers for the profile / custom-rule / CSV tabs that appear
 * in both MMConfigPanels (main config modal) and MMAdvancedToolsModal
 * (legacy alias kept for compatibility). Extracting them avoids
 * duplicating 100+ lines across both components.
 */
export function useMMConfigPanels() {
  const { t } = useI18n()
  const { showToast } = useToast()
  const {
    anomalyRules,
    saveAnomalyRules,
    showAdvancedModal,
    saveProfile,
    applyProfile,
    customRules,
    addCustomRule,
    newNames,
    importRenameCsv,
  } = useMediaManager()

  // ── Profiles ──
  const newProfileName = ref('')

  function applyProfileLocal(p) {
    const cfg = applyProfile(p)
    saveAnomalyRules({
      ...anomalyRules.value,
      _renameFormat: { movie: cfg.movie, tv: cfg.tv },
      _tmdbLang: cfg.lang || anomalyRules.value._tmdbLang,
    })
    showToast(t('mediaManager.profileApplied', { name: p.name }), TOAST_TYPE.OK)
    showAdvancedModal.value = false
    return cfg
  }

  function saveCurrentAsProfile() {
    if (!newProfileName.value.trim()) {
      showToast(t('mediaManager.enterProfileName'), TOAST_TYPE.WARN)
      return false
    }
    const fmt = anomalyRules.value._renameFormat || {
      movie: '{t} ({y})',
      tv: '{n} - {s00e00} - {t}',
    }
    const lang = anomalyRules.value._tmdbLang || 'fr-FR'
    saveProfile(newProfileName.value.trim(), { ...fmt, lang })
    newProfileName.value = ''
    return true
  }

  // ── Custom rules ──
  const newRule = ref({ from: '', to: '', isRegex: false, flags: 'gi' })

  function addRuleLocal() {
    if (!newRule.value.from) return
    addCustomRule({
      from: newRule.value.from,
      to: newRule.value.to,
      type: newRule.value.isRegex ? RULE_TYPE.REGEX : RULE_TYPE.REPLACE,
      flags: newRule.value.isRegex ? newRule.value.flags : '',
      enabled: true,
    })
    newRule.value = { from: '', to: '', isRegex: false, flags: 'gi' }
    showToast(t('mediaManager.ruleAdded'), TOAST_TYPE.OK)
  }

  function saveRulesChange() {
    try {
      localStorage.setItem('mk_custom_rules', JSON.stringify(customRules.value))
    } catch {
      /* silent: localStorage quota/privacy mode */
    }
  }

  // ── CSV import/export ──
  const csvDragOver = ref(false)
  const csvPreview = ref([])

  async function dropCsv(e) {
    csvDragOver.value = false
    const f = e.dataTransfer?.files?.[0]
    if (f) await loadCsvFile(f)
  }

  async function pickCsvFile(e) {
    const f = e.target?.files?.[0]
    if (f) await loadCsvFile(f)
  }

  async function loadCsvFile(file) {
    try {
      csvPreview.value = await importRenameCsv(file)
      showToast(t('mediaManager.csvLinesLoaded', { count: csvPreview.value.length }), TOAST_TYPE.OK)
    } catch {
      showToast(t('mediaManager.csvError'), TOAST_TYPE.ERR)
    }
  }

  function applyCsvImport() {
    newNames.value = csvPreview.value.map(r => ({
      name: r.newName + (r.ext ? '.' + r.ext : ''),
      oldName: r.oldName,
      ext: r.ext || '',
      path: '',
      mismatch: false,
      mismatchStrong: false,
    }))
    csvPreview.value = []
    showAdvancedModal.value = false
    showToast(t('mediaManager.namesLoaded', { count: newNames.value.length }), TOAST_TYPE.OK)
  }

  function downloadCsvTemplate() {
    const rows = [
      'Old name,New name,Extension,Status',
      '"My.Movie.2024.HDRip.mkv","My Movie (2024).mkv","mkv","To rename"',
      '"Show.S01E01.VOSTFR.mp4","My Show - S01E01 - Pilot.mp4","mp4","To rename"',
    ]
    const blob = new Blob(['\ufeff' + rows.join('\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rename_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    newProfileName,
    applyProfileLocal,
    saveCurrentAsProfile,
    newRule,
    addRuleLocal,
    saveRulesChange,
    csvDragOver,
    csvPreview,
    dropCsv,
    pickCsvFile,
    applyCsvImport,
    downloadCsvTemplate,
  }
}
