import { computed } from 'vue'
import {
  apiGet,
  apiPut,
  apiPost,
  showToast,
  _t,
  CATS,
  activeCat,
  filtered,
  anomalyRules,
  namingIssues,
  analysisActive,
  renameProfiles,
  DEFAULT_PROFILES,
  _saveProfiles,
  customRules,
  _saveCustomRules,
  releaseTags,
  releaseTagsDefaults,
  releaseTagsLoaded,
  newNames,
  crossCatDuplicates,
  checkingDuplicates,
} from './mediaManagerState'
import { NAMING_PATTERNS } from './mediaManagerState'
import { applyFilter } from './mediaManagerNavigation'
import { TOAST_TYPE } from '@/constants/toast'
import { FILE_TYPE, RULE_TYPE } from '@/constants/mediaManager'

// ─── ANOMALIES ───
export function saveAnomalyRules(rules) {
  anomalyRules.value = { ...rules }
  try {
    localStorage.setItem('mk_anomaly_rules', JSON.stringify(rules))
  } catch {
    /* silent: localStorage quota/privacy mode */
  }
}
export const issuesCount = computed(() => Object.keys(namingIssues.value).length)

export function analyzeNames() {
  const rules = anomalyRules.value
  const issues = {}
  for (const f of filtered.value.filter(f => f.type === FILE_TYPE.FILE)) {
    const fi = []
    const nameNoExt = f.name.replace(/\.[^.]+$/, '')
    if (rules.checkResolution && !NAMING_PATTERNS.resolution.test(f.name))
      fi.push({ type: 'resolution', message: 'Missing resolution', severity: 'warn' })
    if (
      rules.checkYear &&
      !NAMING_PATTERNS.year.test(f.name) &&
      !NAMING_PATTERNS.episode.test(f.name)
    )
      fi.push({ type: 'year', message: 'Missing year', severity: 'info' })
    if (rules.checkDoubleSpaces && /\s{2,}/.test(nameNoExt))
      fi.push({ type: 'spacing', message: 'Double spaces', severity: 'warn' })
    if (rules.checkMultipleUnderscores && /_{2,}/.test(nameNoExt))
      fi.push({ type: 'underscores', message: 'Multiple underscores', severity: 'warn' })
    if (rules.checkNameLength && f.name.length > rules.maxNameLength)
      fi.push({ type: 'length', message: `Name too long (${f.name.length})`, severity: 'err' })
    if (rules.checkDotsCount && (nameNoExt.match(/\./g) || []).length > rules.maxDots)
      fi.push({ type: 'dots', message: 'Too many dots', severity: 'warn' })
    if (fi.length > 0) issues[f.path] = fi
  }
  namingIssues.value = issues
  analysisActive.value = true
  // Re-trigger filter/sort so anomalies bubble up.
  applyFilter()
  const total = Object.keys(issues).length
  showToast(
    total > 0
      ? _t('mediaManager.filesWithAnomalies', { count: total })
      : _t('mediaManager.noAnomalies'),
    total > 0 ? TOAST_TYPE.WARN : TOAST_TYPE.OK,
  )
}
export function clearAnalysis() {
  namingIssues.value = {}
  analysisActive.value = false
  applyFilter()
}

// ─── PROFILES ───
export function getAllProfiles() {
  return [...DEFAULT_PROFILES, ...renameProfiles.value]
}
export function saveProfile(name, config) {
  const id = 'profile-' + Date.now()
  renameProfiles.value.push({ id, name, builtin: false, config })
  _saveProfiles()
  showToast(_t('mediaManager.profileSaved', { name }), TOAST_TYPE.OK)
}
export function deleteProfile(id) {
  renameProfiles.value = renameProfiles.value.filter(p => p.id !== id)
  _saveProfiles()
}
export function applyProfile(profile) {
  return profile.config
}

// ─── CUSTOM RULES ───
export function addCustomRule(rule) {
  customRules.value.push({ id: Date.now(), ...rule })
  _saveCustomRules()
}
export function deleteCustomRule(id) {
  customRules.value = customRules.value.filter(r => r.id !== id)
  _saveCustomRules()
}
export function applyCustomRules(name) {
  let result = name
  for (const rule of customRules.value) {
    if (!rule.enabled) continue
    try {
      if (rule.type === RULE_TYPE.REPLACE) result = result.split(rule.from).join(rule.to)
      else if (rule.type === RULE_TYPE.REGEX)
        result = result.replace(new RegExp(rule.from, rule.flags || 'gi'), rule.to)
    } catch {
      /* silent: invalid user regex → skip this rule */
    }
  }
  return result
}

// ─── RELEASE TAGS (admin-managed list, persisted server-side) ───
export async function loadReleaseTags(force = false) {
  if (releaseTagsLoaded.value && !force) return
  try {
    const data = await apiGet('/api/media/release-tags')
    releaseTags.value = Array.isArray(data?.tags) ? data.tags : []
    releaseTagsDefaults.value = Array.isArray(data?.defaults) ? data.defaults : []
  } catch {
    releaseTags.value = []
    releaseTagsDefaults.value = []
  }
  releaseTagsLoaded.value = true
}
export async function saveReleaseTags(tags) {
  try {
    const data = await apiPut('/api/media/release-tags', { tags })
    releaseTags.value = Array.isArray(data?.tags) ? data.tags : []
    showToast(_t('mediaManager.releaseTagsSaved'), TOAST_TYPE.OK)
    return true
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
    return false
  }
}
export async function resetReleaseTags() {
  try {
    const data = await apiPost('/api/media/release-tags/reset')
    releaseTags.value = Array.isArray(data?.tags) ? data.tags : []
    showToast(_t('mediaManager.releaseTagsReset'), TOAST_TYPE.OK)
    return true
  } catch {
    showToast(_t('common.networkError'), TOAST_TYPE.ERR)
    return false
  }
}

// ─── CROSS-CATEGORY DUPLICATES ───
export async function findCrossCatDuplicates(targetNames) {
  const conflicts = []
  for (const cat of CATS.value) {
    if (cat.key === activeCat.value) continue
    try {
      const data = await apiGet(`/api/media/files/${cat.key}`)
      if (!Array.isArray(data)) continue
      for (const f of data) {
        for (const n of targetNames) {
          if (f.name.toLowerCase() === n.toLowerCase()) {
            conflicts.push({ name: f.name, cat: cat.label, path: f.path })
          }
        }
      }
    } catch {
      /* silent: per-category fetch error skipped, others still scan */
    }
  }
  return conflicts
}

export async function checkCrossCatDuplicates() {
  checkingDuplicates.value = true
  const names = newNames.value.map(n => n.name)
  crossCatDuplicates.value = await findCrossCatDuplicates(names)
  checkingDuplicates.value = false
  if (crossCatDuplicates.value.length)
    showToast(
      _t('mediaManager.duplicatesDetected', { count: crossCatDuplicates.value.length }),
      TOAST_TYPE.WARN,
    )
  else showToast(_t('mediaManager.noDuplicates'), TOAST_TYPE.OK)
}

// ─── EXPORT / IMPORT CSV ───
export function exportRenameCsv(names) {
  const rows = ['Old name,New name,Extension,Status']
  for (const n of names) {
    const old = n.oldName || ''
    const nw = n.name || ''
    const ext = n.ext || ''
    const status = n.path ? 'To rename' : 'Generated'
    rows.push(`"${old.replace(/"/g, '""')}","${nw.replace(/"/g, '""')}","${ext}","${status}"`)
  }
  const blob = new Blob(['\ufeff' + rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `renommage_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function importRenameCsv(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = e => {
      try {
        const lines = e.target.result
          .replace(/^\uFEFF/, '')
          .split('\n')
          .filter(Boolean)
        lines.shift()
        const pairs = []
        for (const line of lines) {
          const cols =
            line
              .match(/("(?:[^"]|"")*"|[^,]*)/g)
              ?.map(c => c.replace(/^"|"$/g, '').replace(/""/g, '"')) || []
          if (cols[0] && cols[1])
            pairs.push({ oldName: cols[0], newName: cols[1], ext: cols[2] || '' })
        }
        resolve(pairs)
      } catch (e) {
        reject(e)
      }
    }
    reader.onerror = reject
    reader.readAsText(file, 'utf-8')
  })
}
