<template>
  <div class="mm-overlay" :class="{ show: showConfigPanel }" @click.self="showConfigPanel = false">
    <div class="mm-config-modal">
      <div class="mm-config-sidebar">
        <div class="mm-config-sidebar-title">
          <Settings :size="14" />
          {{ $t('mediaManager.configTitle') }}
        </div>
        <button
          v-for="tab in configTabs"
          :key="tab.id"
          class="mm-config-tab"
          :class="{ active: configTab === tab.id, 'mm-tab-saved': savedTab === tab.id }"
          @click="configTab = tab.id"
        >
          <component :is="tab.icon" :size="13" />
          {{ tab.label }}
        </button>
      </div>
      <div class="mm-config-content">
        <div class="mm-config-header">
          <span>{{ configTabs.find(t => t.id === configTab)?.label }}</span>
          <button
            class="mm-btn-sm mm-close-btn"
            type="button"
            :aria-label="$t('common.close')"
            @click="showConfigPanel = false"
          >
            <X :size="14" />
          </button>
        </div>

        <div v-if="configTab === 'format'" class="mm-config-body">
          <div class="mm-rf-syntax">{{ $t('mediaManager.formatSyntaxHint') }}</div>
          <div class="mm-section mm-section-lg">
            <div class="mm-label">{{ $t('mediaManager.formatMovies') }}</div>
            <input
              v-model="renameFormatDraft.movie"
              class="mm-folder-input mm-input-mono"
              placeholder="{t} ({y})"
            />
            <div class="mm-rf-preview">
              {{ $t('mediaManager.formatPreview') }}
              <span class="mm-rf-ex">{{ previewMovie }}</span>
            </div>
          </div>
          <div class="mm-section">
            <div class="mm-label">{{ $t('mediaManager.formatSeries') }}</div>
            <input
              v-model="renameFormatDraft.tv"
              class="mm-folder-input mm-input-mono"
              placeholder="{n} - {s00e00} - {t}"
            />
            <div class="mm-rf-preview">
              {{ $t('mediaManager.formatPreview') }}
              <span class="mm-rf-ex">{{ previewTv }}</span>
            </div>
          </div>
          <div class="mm-section mm-section-lg">
            <div class="mm-label mm-label-gap">{{ $t('mediaManager.formatExamples') }}</div>
            <div class="mm-rf-examples">
              <div
                v-for="ex in RF_EXAMPLES"
                :key="ex.f"
                class="mm-rf-ex-row mm-clickable"
                :title="$t('mediaManager.clickToUse')"
                @click="renameFormatDraft.tv = ex.f"
              >
                <code class="mm-rf-code">{{ ex.f }}</code>
                <span class="mm-rf-arrow">→</span>
                <span class="mm-rf-result">{{ ex.r }}</span>
              </div>
            </div>
          </div>
          <div class="mm-config-footer">
            <button
              class="mm-btn-sm mm-btn-success"
              :class="{ 'mm-btn-saved': savedTab === 'format' }"
              @click="saveRenameFormat"
            >
              <Check />
              {{
                savedTab === 'format'
                  ? $t('mediaManager.savedBtnLabel')
                  : $t('mediaManager.saveBtnLabel')
              }}
            </button>
          </div>
        </div>

        <div v-if="configTab === 'profiles'" class="mm-config-body">
          <p class="mm-desc">{{ $t('mediaManager.profilesDesc') }}</p>
          <div class="mm-label mm-label-gap">{{ $t('mediaManager.availableProfiles') }}</div>
          <div class="mm-profile-list">
            <div v-for="profile in getAllProfiles()" :key="profile.id" class="mm-profile-row">
              <div class="mm-profile-info">
                <span class="mm-profile-name">{{ profile.name }}</span>
                <span class="mm-profile-meta">
                  {{ profile.config.movie }} · {{ profile.config.tv }}
                </span>
              </div>
              <div class="mm-profile-actions">
                <button
                  class="mm-btn-sm mm-btn-accent mm-profile-use-btn"
                  @click="onApplyProfile(profile)"
                >
                  {{ $t('common.use') }}
                </button>
                <button
                  v-if="!profile.builtin"
                  class="mm-btn-sm mm-profile-del-btn"
                  @click="deleteProfile(profile.id)"
                >
                  ✕
                </button>
              </div>
            </div>
          </div>
          <div class="mm-label mm-label-gap">{{ $t('mediaManager.saveCurrentProfile') }}</div>
          <div class="mm-field-row">
            <input
              v-model="newProfileName"
              class="mm-folder-input mm-input-flat mm-input-flex"
              :placeholder="$t('mediaManager.profileNamePlaceholder')"
              @keydown.enter="onSaveProfile"
            />
            <button
              class="mm-btn-sm mm-btn-success"
              :class="{ 'mm-btn-saved': savedTab === 'profiles' }"
              @click="onSaveProfile"
            >
              <Check />
              {{
                savedTab === 'profiles'
                  ? $t('mediaManager.savedBtnProfile')
                  : $t('mediaManager.saveBtnProfile')
              }}
            </button>
          </div>
        </div>

        <div v-if="configTab === 'anomaly'" class="mm-config-body">
          <p class="mm-desc">{{ $t('mediaManager.anomalyDesc') }}</p>
          <div class="mm-rule-stack">
            <label class="mm-rule-row">
              <input v-model="anomalyDraft.checkResolution" type="checkbox" class="mm-chkbox" />
              <div>
                <div class="mm-rule-label">{{ $t('mediaManager.ruleResolution') }}</div>
                <div class="mm-rule-hint">{{ $t('mediaManager.ruleResolutionHint') }}</div>
              </div>
            </label>
            <label class="mm-rule-row">
              <input v-model="anomalyDraft.checkYear" type="checkbox" class="mm-chkbox" />
              <div>
                <div class="mm-rule-label">{{ $t('mediaManager.ruleYear') }}</div>
                <div class="mm-rule-hint">{{ $t('mediaManager.ruleYearHint') }}</div>
              </div>
            </label>
            <label class="mm-rule-row">
              <input v-model="anomalyDraft.checkDoubleSpaces" type="checkbox" class="mm-chkbox" />
              <div>
                <div class="mm-rule-label">{{ $t('mediaManager.ruleDoubleSpaces') }}</div>
                <div class="mm-rule-hint">{{ $t('mediaManager.ruleDoubleSpacesHint') }}</div>
              </div>
            </label>
            <label class="mm-rule-row">
              <input
                v-model="anomalyDraft.checkMultipleUnderscores"
                type="checkbox"
                class="mm-chkbox"
              />
              <div>
                <div class="mm-rule-label">{{ $t('mediaManager.ruleUnderscores') }}</div>
                <div class="mm-rule-hint">{{ $t('mediaManager.ruleUnderscoresHint') }}</div>
              </div>
            </label>
            <label class="mm-rule-row">
              <input v-model="anomalyDraft.checkDotsCount" type="checkbox" class="mm-chkbox" />
              <div class="mm-rule-text">
                <div class="mm-rule-label">{{ $t('mediaManager.ruleDots') }}</div>
                <div class="mm-rule-hint">{{ $t('mediaManager.ruleDotsHint') }}</div>
              </div>
              <div class="mm-rule-max">
                <span class="mm-rule-max-label">{{ $t('mediaManager.ruleMax') }}</span>
                <input
                  v-model.number="anomalyDraft.maxDots"
                  type="number"
                  min="1"
                  max="20"
                  class="mm-rule-num"
                  :disabled="!anomalyDraft.checkDotsCount"
                />
              </div>
            </label>
            <label class="mm-rule-row">
              <input v-model="anomalyDraft.checkNameLength" type="checkbox" class="mm-chkbox" />
              <div class="mm-rule-text">
                <div class="mm-rule-label">{{ $t('mediaManager.ruleLength') }}</div>
                <div class="mm-rule-hint">{{ $t('mediaManager.ruleLengthHint') }}</div>
              </div>
              <div class="mm-rule-max">
                <span class="mm-rule-max-label">{{ $t('mediaManager.ruleMax') }}</span>
                <input
                  v-model.number="anomalyDraft.maxNameLength"
                  type="number"
                  min="50"
                  max="500"
                  class="mm-rule-num"
                  :disabled="!anomalyDraft.checkNameLength"
                />
              </div>
            </label>
          </div>
          <div class="mm-config-footer">
            <button
              class="mm-btn-sm mm-btn-success"
              :class="{ 'mm-btn-saved': savedTab === 'anomaly' }"
              @click="saveAnomalyConfig"
            >
              <Check />
              {{ savedTab === 'anomaly' ? $t('common.saved') + ' ✓' : $t('common.save') }}
            </button>
          </div>
        </div>

        <div v-if="configTab === 'lang'" class="mm-config-body">
          <p class="mm-desc">{{ $t('mediaManager.langDesc') }}</p>
          <div class="mm-label">{{ $t('mediaManager.renameLanguage') }}</div>
          <div class="mm-lang-stack">
            <label v-for="lang in TMDB_LANGS" :key="lang.code" class="mm-rule-row mm-clickable">
              <input
                v-model="tmdbLangDraft"
                type="radio"
                :value="lang.code"
                class="mm-chkbox mm-radio-accent"
              />
              <div class="mm-rule-text">
                <div class="mm-rule-label">{{ lang.flag }} {{ lang.label }}</div>
                <div class="mm-rule-hint">{{ lang.hint }}</div>
              </div>
              <div class="mm-lang-tags">
                <span v-for="tag in lang.tags" :key="tag" class="mm-lang-tag">{{ tag }}</span>
              </div>
            </label>
          </div>
          <div class="mm-config-footer">
            <button
              class="mm-btn-sm mm-btn-success"
              :class="{ 'mm-btn-saved': savedTab === 'lang' }"
              @click="saveTmdbLang"
            >
              <Check />
              {{ savedTab === 'lang' ? $t('common.saved') + ' ✓' : $t('common.save') }}
            </button>
          </div>
        </div>

        <MMRulesPanel v-if="configTab === 'rules'" />
        <MMReleaseTagsPanel v-if="configTab === 'releaseTags'" />
        <MMCsvPanel v-if="configTab === 'csv'" />
        <MMDupesPanel v-if="configTab === 'dupes'" />
      </div>
    </div>
  </div>

  <MMAdvancedToolsModal />
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaManager } from '@/composables/useMediaManager'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useMMConfigPanels } from '@/composables/useMMConfigPanels'
import MMAdvancedToolsModal from './MMAdvancedToolsModal.vue'
import MMRulesPanel from './MMRulesPanel.vue'
import MMReleaseTagsPanel from './MMReleaseTagsPanel.vue'
import MMCsvPanel from './MMCsvPanel.vue'
import MMDupesPanel from './MMDupesPanel.vue'
import {
  Briefcase,
  Check,
  CircleCheck,
  Code2,
  Copy,
  FileDown,
  Languages,
  Settings,
  Tags,
  X,
} from 'lucide-vue-next'

const { t } = useI18n()
const { showToast } = useToast()

const { anomalyRules, saveAnomalyRules, getAllProfiles, deleteProfile } = useMediaManager()

const { newProfileName, applyProfileLocal, saveCurrentAsProfile } = useMMConfigPanels()

const showConfigPanel = defineModel('showConfigPanel', { type: Boolean, default: false })
const configTab = ref('format')
const configTabs = [
  { id: 'format', label: t('mediaManager.renameFormatLabel'), icon: Code2 },
  { id: 'profiles', label: t('mediaManager.profilesTab'), icon: Briefcase },
  { id: 'anomaly', label: t('mediaManager.anomalyRulesLabel'), icon: CircleCheck },
  { id: 'lang', label: t('mediaManager.tmdbLangLabel'), icon: Languages },
  { id: 'rules', label: t('mediaManager.customRulesTab'), icon: Code2 },
  { id: 'releaseTags', label: t('mediaManager.releaseTagsTab'), icon: Tags },
  { id: 'csv', label: t('mediaManager.csvTab'), icon: FileDown },
  { id: 'dupes', label: t('mediaManager.crossCatDupesTab'), icon: Copy },
]

const savedTab = ref(null)
function _flashSaved(tab) {
  savedTab.value = tab
  setTimeout(() => {
    savedTab.value = null
  }, 1800)
}

const renameFormatDraft = ref({ movie: '{t} ({y})', tv: '{n} - {s00e00} - {t}' })
const RF_EXAMPLES = [
  { f: '{n} - {s00e00} - {t}', r: 'SeriesName - S01E01 - EpisodeName' },
  { f: '{n} - {sxe} - {t} {subt}', r: 'SeriesName - 1x01 - EpisodeName VOSTFR' },
  { f: '{t} ({y})', r: 'MovieName (2005)' },
  { f: '{n} [{airdate}] {t}', r: 'SeriesName [2002-12-20] EpisodeName' },
]
const TMDB_LANGS = [
  {
    code: 'fr-FR',
    flag: '🇫🇷',
    label: 'French',
    hint: 'Titles and episodes in French',
    tags: ['MULTI', 'VOSTFR', 'VFF', 'VFI', 'VO', 'VOSTA'],
  },
  {
    code: 'en-US',
    flag: '🇺🇸',
    label: 'English',
    hint: 'Titles and episodes in English',
    tags: ['MULTI', 'DUBBED', 'SUB', 'VO'],
  },
  {
    code: 'de-DE',
    flag: '🇩🇪',
    label: 'German',
    hint: 'Titles and episodes in German',
    tags: ['MULTI', 'DUBBED', 'SUB', 'OV'],
  },
  {
    code: 'es-ES',
    flag: '🇪🇸',
    label: 'Spanish',
    hint: 'Titles and episodes in Spanish',
    tags: ['MULTI', 'VOSE', 'CAST', 'VO'],
  },
  {
    code: 'it-IT',
    flag: '🇮🇹',
    label: 'Italian',
    hint: 'Titles and episodes in Italian',
    tags: ['MULTI', 'DUBBED', 'SUB', 'OV'],
  },
  {
    code: 'pt-BR',
    flag: '🇧🇷',
    label: 'Portuguese',
    hint: 'Titles and episodes in Portuguese',
    tags: ['MULTI', 'DUBLADO', 'LEG', 'VO'],
  },
  {
    code: 'ja-JP',
    flag: '🇯🇵',
    label: 'Japanese',
    hint: 'Titles and episodes in Japanese',
    tags: ['MULTI', 'VOSTFR', 'VOSTA', 'RAW'],
  },
]
const tmdbLangDraft = ref('fr-FR')
const anomalyDraft = ref({})

function openConfigPanel(tab = 'format') {
  configTab.value = tab
  renameFormatDraft.value = {
    ...(anomalyRules.value._renameFormat || { movie: '{t} ({y})', tv: '{n} - {s00e00} - {t}' }),
  }
  anomalyDraft.value = { ...anomalyRules.value }
  tmdbLangDraft.value = anomalyRules.value._tmdbLang || 'fr-FR'
  showConfigPanel.value = true
}

defineExpose({ openConfigPanel })

const currentLangTags = computed(() => {
  const saved = anomalyRules.value._tmdbLang || 'fr-FR'
  return TMDB_LANGS.find(l => l.code === saved)?.tags || TMDB_LANGS[0].tags
})

const previewMovie = computed(
  () =>
    (renameFormatDraft.value.movie || '…')
      .replace('{n}', 'MovieName')
      .replace('{t}', 'MovieName')
      .replace('{y}', '2005')
      .replace('{s00e00}', '')
      .replace('{sxe}', '')
      .replace('{subt}', '')
      .trim() || '…',
)
const previewTv = computed(
  () =>
    (renameFormatDraft.value.tv || '…')
      .replace('{n}', 'SeriesName')
      .replace('{t}', 'EpisodeName')
      .replace('{y}', '2002')
      .replace('{s00e00}', 'S01E01')
      .replace('{sxe}', '1x01')
      .replace('{subt}', currentLangTags.value[0] || 'VOSTFR')
      .trim() || '…',
)

function saveRenameFormat() {
  saveAnomalyRules({ ...anomalyRules.value, _renameFormat: { ...renameFormatDraft.value } })
  showToast(t('mediaManager.renameFormatSaved'), TOAST_TYPE.OK)
  _flashSaved('format')
}
function saveAnomalyConfig() {
  saveAnomalyRules({ ...anomalyDraft.value })
  showToast(t('mediaManager.anomalyRulesSaved'), TOAST_TYPE.OK)
  _flashSaved('anomaly')
}
function saveTmdbLang() {
  saveAnomalyRules({ ...anomalyRules.value, _tmdbLang: tmdbLangDraft.value })
  showToast(t('mediaManager.tmdbLangSaved'), TOAST_TYPE.OK)
  _flashSaved('lang')
}

function onApplyProfile(p) {
  const cfg = applyProfileLocal(p)
  renameFormatDraft.value = { movie: cfg.movie, tv: cfg.tv }
  if (cfg.lang) tmdbLangDraft.value = cfg.lang
}
function onSaveProfile() {
  if (saveCurrentAsProfile()) _flashSaved('profiles')
}
</script>

<style scoped>
.mm-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}
.mm-section {
  margin-top: 0.8rem;
}
.mm-section-lg {
  margin-top: 0.9rem;
}
.mm-label-gap {
  margin-bottom: 0.4rem;
}
.mm-close-btn {
  padding: 3px 8px;
}
.mm-input-mono {
  font-family: monospace;
}
.mm-input-flat {
  margin-top: 0;
}
.mm-input-flex {
  flex: 1;
}
.mm-field-row {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}
.mm-clickable {
  cursor: pointer;
}

.mm-profile-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.9rem;
}
.mm-profile-actions {
  display: flex;
  gap: 0.3rem;
  flex-shrink: 0;
}
.mm-profile-use-btn {
  padding: 2px 8px;
  font-size: var(--text-3xs);
}
.mm-profile-del-btn {
  padding: 2px 6px;
  color: var(--mm-red);
  font-size: var(--text-2xs);
}

.mm-rule-stack {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.mm-rule-text {
  flex: 1;
}
.mm-rule-max {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
}
.mm-rule-max-label {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}

.mm-lang-stack {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 0.4rem;
}
.mm-radio-accent {
  accent-color: var(--accent-500);
}
.mm-lang-tags {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 160px;
}
</style>
