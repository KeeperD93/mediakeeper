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

        <MMFormatPanel
          v-if="configTab === 'format'"
          v-model:rename-format-draft="renameFormatDraft"
          :preview-movie="previewMovie"
          :preview-tv="previewTv"
          :saved="savedTab === 'format'"
          @save="saveRenameFormat"
        />

        <MMProfilesPanel
          v-if="configTab === 'profiles'"
          v-model:new-profile-name="newProfileName"
          :profiles="getAllProfiles()"
          :saved="savedTab === 'profiles'"
          @apply-profile="onApplyProfile"
          @delete-profile="deleteProfile"
          @save-profile="onSaveProfile"
        />

        <MMAnomalyPanel
          v-if="configTab === 'anomaly'"
          v-model:anomaly-draft="anomalyDraft"
          :saved="savedTab === 'anomaly'"
          @save="saveAnomalyConfig"
        />

        <MMLangPanel
          v-if="configTab === 'lang'"
          v-model:tmdb-lang-draft="tmdbLangDraft"
          :saved="savedTab === 'lang'"
          @save="saveTmdbLang"
        />

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
import MMFormatPanel from './MMConfigPanels/MMFormatPanel.vue'
import MMProfilesPanel from './MMConfigPanels/MMProfilesPanel.vue'
import MMAnomalyPanel from './MMConfigPanels/MMAnomalyPanel.vue'
import MMLangPanel from './MMConfigPanels/MMLangPanel.vue'
import { TMDB_LANGS } from './MMConfigPanels/tmdbLangs'
import {
  Briefcase,
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
