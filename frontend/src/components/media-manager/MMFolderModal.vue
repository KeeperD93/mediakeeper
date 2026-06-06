<template>
  <div class="mf-overlay" :class="{ show: modalFolders.show }" @click.self="close">
    <div ref="panelRef" class="mf-modal" role="dialog" aria-modal="true" :aria-labelledby="titleId">
      <header class="mf-header">
        <div class="mf-header-title">
          <Folder :size="16" />
          <h3 :id="titleId">{{ $t('mediaManager.organizeFolders') }}</h3>
          <span v-if="folderExistingDirs.length" class="mf-chip">
            <Files :size="11" />
            {{
              $t(
                'mediaManager.existingFoldersCount',
                { count: folderExistingDirs.length },
                folderExistingDirs.length,
              )
            }}
          </span>
        </div>
        <button ref="closeBtnRef" class="mf-close" :title="$t('common.close')" @click="close">
          <X :size="14" />
        </button>
      </header>

      <div class="mf-body">
        <!-- ── Section 1 : Dossiers existants ── -->
        <section v-if="folderExistingDirs.length" class="mf-section">
          <div class="mf-section-label">{{ $t('mediaManager.existingFolders') }}</div>

          <div class="mf-folder-list">
            <div v-for="(d, i) in folderExistingDirs" :key="d.path" class="mf-folder-card">
              <span class="mf-folder-icon"><Folder :size="14" /></span>
              <span class="mf-folder-old" :title="d.name">{{ d.name }}</span>
              <ArrowRight :size="11" class="mf-folder-arrow" />
              <input
                v-model="folderExistingDirs[i].newName"
                class="mf-folder-input"
                :class="{ dirty: d.newName !== d.name }"
              />
            </div>
          </div>

          <div class="mf-section-label">{{ $t('mediaManager.audioTag') }}</div>
          <div class="mf-tag-row">
            <span
              v-for="tag in audioTagsForLang"
              :key="`b-${tag}`"
              class="mf-tag"
              :class="{ active: folderBatchAudioTags.has(tag) }"
              @click="toggleBatchAudioTag(tag)"
            >
              {{ tag }}
            </span>
          </div>

          <div class="mf-actions-row">
            <button class="mf-btn-secondary" @click="autoDetectFolders">
              <RefreshCw :size="12" />
              {{ $t('mediaManager.autoDetect') }}
            </button>
            <button
              class="mf-btn-accent"
              :disabled="!hasFolderChanges"
              @click="execRenameAllFolders"
            >
              <Check :size="12" />
              {{ $t('mediaManager.renameAll') }}
            </button>
          </div>

          <hr class="mf-divider" />
        </section>

        <!-- ── Section 2 : Nouvelle structure ── -->
        <section class="mf-section">
          <div class="mf-section-label">{{ $t('mediaManager.seriesName') }}</div>
          <div class="mf-input-wrap">
            <Pencil :size="12" />
            <input
              v-model="folderSeriesName"
              :placeholder="$t('mediaManager.seriesNamePlaceholder')"
              @input="updateFolderPreview"
            />
          </div>

          <div class="mf-section-label">{{ $t('mediaManager.audioTag') }}</div>
          <div class="mf-tag-row">
            <span
              v-for="tag in audioTagsForLang"
              :key="`a-${tag}`"
              class="mf-tag"
              :class="{ active: folderAudioTags.has(tag) }"
              @click="toggleAudioTag(tag)"
            >
              {{ tag }}
            </span>
          </div>

          <div v-if="folderSeasonTags.length">
            <div class="mf-section-label">{{ $t('mediaManager.seasonsToCreate') }}</div>
            <div class="mf-tag-row">
              <span
                v-for="s in folderSeasonTags"
                :key="s.season"
                class="mf-tag"
                :class="{ active: s.active }"
                @click="((s.active = !s.active), updateFolderPreview())"
              >
                Saison {{ String(s.season).padStart(2, '0') }}
              </span>
            </div>
          </div>

          <div class="mf-section-label">{{ $t('mediaManager.preview') }}</div>
          <pre class="mf-preview-block">{{ folderPreview }}</pre>
        </section>
      </div>

      <footer class="mf-footer">
        <div class="mf-footer-info">
          <span class="mf-footer-label">{{ $t('mediaManager.seriesName') }}</span>
          <span class="mf-footer-value" :class="{ empty: !trimmedSeriesName }">
            {{ trimmedSeriesName || $t('mediaManager.seriesNameMissingShort') }}
          </span>
        </div>
        <div class="mf-actions">
          <button class="mf-btn-ghost" @click="close">{{ $t('common.close') }}</button>
          <button class="mf-btn-primary" :disabled="!trimmedSeriesName" @click="execFolderOrganize">
            <Check :size="13" />
            {{ $t('mediaManager.rename') }}
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, useId } from 'vue'
import { useMediaManager } from '@/composables/useMediaManager'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { ArrowRight, Check, Files, Folder, Pencil, RefreshCw, X } from 'lucide-vue-next'
import '@/assets/styles/folder-modal.css'

const {
  modalFolders,
  folderExistingDirs,
  folderSeriesName,
  folderAudioTags,
  folderBatchAudioTags,
  folderSeasonTags,
  folderPreview,
  toggleAudioTag,
  toggleBatchAudioTag,
  updateFolderPreview,
  autoDetectFolders,
  execRenameAllFolders,
  execFolderOrganize,
  anomalyRules,
} = useMediaManager()

// Audio tag presets keyed by the user's TMDB language selection.
const TMDB_LANGS = [
  { code: 'fr-FR', tags: ['MULTI', 'VOSTFR', 'VFF', 'VFI', 'VO', 'VOSTA'] },
  { code: 'en-US', tags: ['MULTI', 'DUBBED', 'SUB', 'VO'] },
  { code: 'de-DE', tags: ['MULTI', 'DUBBED', 'SUB', 'OV'] },
  { code: 'es-ES', tags: ['MULTI', 'VOSE', 'CAST', 'VO'] },
  { code: 'it-IT', tags: ['MULTI', 'DUBBED', 'SUB', 'OV'] },
  { code: 'pt-BR', tags: ['MULTI', 'DUBLADO', 'LEG', 'VO'] },
  { code: 'ja-JP', tags: ['MULTI', 'VOSTFR', 'VOSTA', 'RAW'] },
]
const audioTagsForLang = computed(() => {
  const saved = anomalyRules.value._tmdbLang || 'fr-FR'
  return TMDB_LANGS.find(l => l.code === saved)?.tags || TMDB_LANGS[0].tags
})

const trimmedSeriesName = computed(() => (folderSeriesName.value || '').trim())
const hasFolderChanges = computed(() =>
  folderExistingDirs.value.some(d => d.newName && d.newName !== d.name),
)

function close() {
  modalFolders.value.show = false
}

const panelRef = ref(null)
const closeBtnRef = ref(null)
const titleId = useId()
const folderModalActive = computed(() => modalFolders.value.show)

useFocusTrap({
  active: folderModalActive,
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
})
</script>
