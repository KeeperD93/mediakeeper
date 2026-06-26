<template>
  <div
    class="mm-overlay"
    :class="{ show: fileMetaModal.show }"
    :inert="!fileMetaModal.show"
    @click.self="closeFileMeta"
  >
    <div
      ref="metaPanelRef"
      class="mm-modal mm-modal-560"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      tabindex="-1"
    >
      <h3 :id="titleId">
        <Info />
        {{ $t('mediaManager.metadataTitle') }}
      </h3>
      <div class="mm-modal-body mm-meta-body">
        <div v-if="fileMetaModal.loading" class="mm-state">
          <MkSpinner size="sm" />
          <span>{{ $t('mediaManager.analyzingFile') }}</span>
        </div>
        <template v-else-if="fileMetaModal.file">
          <div class="mm-info-name">{{ fileMetaModal.file.name }}</div>
          <div class="mm-info-section-title">
            <FileText :size="11" />
            {{ $t('mediaManager.fileSection') }}
          </div>
          <div class="mm-info-grid">
            <span class="mm-info-label">{{ $t('mediaManager.fileSize') }}</span>
            <span class="mm-info-val">
              {{
                formatBytes(fileMetaModal.data?.size_bytes, locale) ||
                fileMetaModal.file.size_label ||
                '—'
              }}
            </span>
            <span class="mm-info-label">{{ $t('mediaManager.fileDuration') }}</span>
            <span class="mm-info-val">
              {{ formatDuration(fileMetaModal.data?.duration_seconds) || '—' }}
            </span>
            <span class="mm-info-label">{{ $t('mediaManager.fileBitrate') }}</span>
            <span class="mm-info-val">
              {{ formatBitrate(fileMetaModal.data?.overall_bitrate_bps, locale) || '—' }}
            </span>
            <span class="mm-info-label">{{ $t('mediaManager.fileModified') }}</span>
            <span class="mm-info-val">
              {{
                fileMetaModal.file.mtime
                  ? localizedDate(new Date(fileMetaModal.file.mtime * 1000), {
                      day: '2-digit',
                      month: 'long',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '—'
              }}
            </span>
            <span class="mm-info-label">{{ $t('mediaManager.filePath') }}</span>
            <span class="mm-info-val mm-info-path">{{ fileMetaModal.file.path }}</span>
          </div>
          <template v-if="fileMetaModal.data?.video_tracks?.length">
            <div class="mm-info-section-title">
              <Video :size="11" />
              {{ $t('mediaManager.videoSection') }}
            </div>
            <div
              v-for="(t, ti) in fileMetaModal.data.video_tracks"
              :key="'v' + ti"
              class="mm-track-card"
            >
              <div class="mm-track-badges">
                <span v-if="t.codec" class="mm-track-badge mm-badge-codec">{{ t.codec }}</span>
                <span v-if="t.hdr_type" class="mm-track-badge mm-badge-hdr">
                  {{ hdrLabel(t.hdr_type) }}
                </span>
                <span v-if="t.resolution" class="mm-track-badge">{{ t.resolution }}</span>
                <span v-if="t.fps" class="mm-track-badge">{{ t.fps }}</span>
                <span v-if="t.bitrate_bps" class="mm-track-badge">
                  {{ formatBitrate(t.bitrate_bps, locale) }}
                </span>
                <span v-if="t.profile" class="mm-track-badge mm-badge-dim">{{ t.profile }}</span>
              </div>
              <div v-if="t.title" class="mm-track-title">{{ t.title }}</div>
            </div>
          </template>
          <template v-if="fileMetaModal.data?.audio_tracks?.length">
            <div class="mm-info-section-title">
              <Volume2 :size="11" />
              {{
                $t('mediaManager.audioTracksWithCount', {
                  count: fileMetaModal.data.audio_tracks.length,
                })
              }}
            </div>
            <div
              v-for="(t, ti) in fileMetaModal.data.audio_tracks"
              :key="'a' + ti"
              class="mm-track-card"
              :class="{ 'mm-track-default': t.is_default }"
            >
              <div class="mm-track-badges">
                <span v-if="t.language_code" class="mm-track-badge mm-badge-lang">
                  {{ languageLabel(t.language_code, $t) }}
                </span>
                <span v-if="t.codec" class="mm-track-badge mm-badge-codec">{{ t.codec }}</span>
                <span v-if="t.channels" class="mm-track-badge">
                  {{ channelsLabel(t.channels, $t) }}
                </span>
                <span v-if="t.bitrate_bps" class="mm-track-badge">
                  {{ formatBitrate(t.bitrate_bps, locale) }}
                </span>
                <span v-if="t.is_default" class="mm-track-badge mm-badge-default">
                  {{ $t('mediaManager.trackDefault') }}
                </span>
                <span v-if="t.is_commentary" class="mm-track-badge mm-badge-dim">
                  {{ $t('mediaManager.trackComment') }}
                </span>
              </div>
              <div v-if="t.title" class="mm-track-title">{{ t.title }}</div>
            </div>
          </template>
          <template v-if="fileMetaModal.data?.subtitle_tracks?.length">
            <div class="mm-info-section-title">
              <Captions :size="11" />
              {{
                $t('mediaManager.subtitleTracksWithCount', {
                  count: fileMetaModal.data.subtitle_tracks.length,
                })
              }}
            </div>
            <div
              v-for="(t, ti) in fileMetaModal.data.subtitle_tracks"
              :key="'s' + ti"
              class="mm-track-card"
              :class="{ 'mm-track-default': t.is_default }"
            >
              <div class="mm-track-badges">
                <span v-if="t.language_code" class="mm-track-badge mm-badge-lang">
                  {{ languageLabel(t.language_code, $t) }}
                </span>
                <span v-if="t.codec" class="mm-track-badge mm-badge-dim">{{ t.codec }}</span>
                <span v-if="t.is_forced" class="mm-track-badge mm-badge-warn">
                  {{ $t('mediaManager.trackForced') }}
                </span>
                <span v-if="t.is_hearing_impaired" class="mm-track-badge mm-badge-dim">SDH</span>
                <span v-if="t.is_default" class="mm-track-badge mm-badge-default">
                  {{ $t('mediaManager.trackDefault') }}
                </span>
              </div>
              <div v-if="t.title" class="mm-track-title">{{ t.title }}</div>
            </div>
          </template>
          <template v-if="fileMetaModal.parsed && Object.keys(fileMetaModal.parsed).length">
            <div class="mm-info-section-title">{{ $t('mediaManager.detectedFromName') }}</div>
            <div class="mm-info-grid">
              <template v-for="(val, key) in fileMetaModal.parsed" :key="key">
                <span class="mm-info-label">{{ metaKeyLabel(key) }}</span>
                <span class="mm-info-val">
                  <span v-if="key === 'langues'" class="mm-info-tags">
                    <span
                      v-for="tag in val.split(', ')"
                      :key="tag"
                      class="mm-lang-tag mm-lang-tag-sm"
                    >
                      {{ tag }}
                    </span>
                  </span>
                  <span v-else-if="key === 'team'" class="mm-info-team">{{ val }}</span>
                  <span v-else>{{ val }}</span>
                </span>
              </template>
            </div>
          </template>
          <div v-if="!fileMetaModal.data && !fileMetaModal.parsed" class="mm-state mm-state-cannot">
            <span class="mm-state-cannot-text">{{ $t('mediaManager.cannotAnalyze') }}</span>
          </div>
        </template>
      </div>
      <div class="mm-modal-footer">
        <button class="mm-btn-sm" @click="closeFileMeta">{{ $t('common.close') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaManager } from '@/composables/useMediaManager'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { Captions, FileText, Info, Video, Volume2 } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'
import { localizedDate } from '@/utils/datetime'
import {
  formatBytes,
  formatDuration,
  formatBitrate,
  hdrLabel,
  channelsLabel,
  languageLabel,
} from '@/utils/mediaMeta'

const { fileMetaModal, closeFileMeta } = useMediaManager()
// Aliased: the template uses ``t`` as the per-track v-for variable.
const { t: translate, locale } = useI18n()

const metaPanelRef = ref(null)
const titleId = useId()
useFocusTrap({
  active: computed(() => fileMetaModal.value.show),
  containerRef: metaPanelRef,
  onEscape: closeFileMeta,
})

function metaKeyLabel(key) {
  // Labels for the filename-parsed metadata grid, localized per viewer.
  // Unknown keys (no i18n entry) fall back to the raw key.
  const k = `mediaManager.detectedFields.${key}`
  const label = translate(k)
  return label === k ? key : label
}
</script>

<style scoped>
/* Modal size */
.mm-modal-560 {
  width: 560px;
}
/* Body scroll height */
.mm-meta-body {
  max-height: 560px;
}
/* File path: multiline wrap + muted small text */
.mm-info-path {
  font-size: 0.63rem;
  word-break: break-all;
  color: var(--text-muted);
}
/* Smaller size for language tags inside the metadata grid */
.mm-lang-tag-sm {
  font-size: 0.6rem;
}
/* "Cannot analyze" empty state */
.mm-state-cannot {
  padding: 0.5rem 0;
}
.mm-state-cannot-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
