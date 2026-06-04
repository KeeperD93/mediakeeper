<template>
  <div class="mm-overlay" :class="{ show: fileMetaModal.show }" @click.self="closeFileMeta">
    <div class="mm-modal mm-modal-560">
      <h3>
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
              {{ fileMetaModal.data?.taille || fileMetaModal.file.size_label || '—' }}
            </span>
            <span class="mm-info-label">{{ $t('mediaManager.fileDuration') }}</span>
            <span class="mm-info-val">{{ fileMetaModal.data?.duree || '—' }}</span>
            <span class="mm-info-label">{{ $t('mediaManager.fileBitrate') }}</span>
            <span class="mm-info-val">{{ fileMetaModal.data?.debit_global || '—' }}</span>
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
          <template v-if="fileMetaModal.data?.pistes_video?.length">
            <div class="mm-info-section-title">
              <Video :size="11" />
              {{ $t('mediaManager.videoSection') }}
            </div>
            <div
              v-for="(t, ti) in fileMetaModal.data.pistes_video"
              :key="'v' + ti"
              class="mm-track-card"
            >
              <div class="mm-track-badges">
                <span v-if="t.codec" class="mm-track-badge mm-badge-codec">{{ t.codec }}</span>
                <span v-if="t.hdr" class="mm-track-badge mm-badge-hdr">{{ t.hdr }}</span>
                <span v-if="t.resolution" class="mm-track-badge">{{ t.resolution }}</span>
                <span v-if="t.fps" class="mm-track-badge">{{ t.fps }}</span>
                <span v-if="t.bitrate" class="mm-track-badge">{{ t.bitrate }}</span>
                <span v-if="t.profil" class="mm-track-badge mm-badge-dim">{{ t.profil }}</span>
              </div>
              <div v-if="t.titre" class="mm-track-title">{{ t.titre }}</div>
            </div>
          </template>
          <template v-if="fileMetaModal.data?.pistes_audio?.length">
            <div class="mm-info-section-title">
              <Volume2 :size="11" />
              {{
                $t('mediaManager.audioTracksWithCount', {
                  count: fileMetaModal.data.pistes_audio.length,
                })
              }}
            </div>
            <div
              v-for="(t, ti) in fileMetaModal.data.pistes_audio"
              :key="'a' + ti"
              class="mm-track-card"
              :class="{ 'mm-track-default': t.par_defaut }"
            >
              <div class="mm-track-badges">
                <span v-if="t.langue" class="mm-track-badge mm-badge-lang">{{ t.langue }}</span>
                <span v-if="t.codec" class="mm-track-badge mm-badge-codec">{{ t.codec }}</span>
                <span v-if="t.canaux" class="mm-track-badge">{{ t.canaux }}</span>
                <span v-if="t.bitrate" class="mm-track-badge">{{ t.bitrate }}</span>
                <span v-if="t.par_defaut" class="mm-track-badge mm-badge-default">
                  {{ $t('mediaManager.trackDefault') }}
                </span>
                <span v-if="t.commentaire" class="mm-track-badge mm-badge-dim">
                  {{ $t('mediaManager.trackComment') }}
                </span>
              </div>
              <div v-if="t.titre" class="mm-track-title">{{ t.titre }}</div>
            </div>
          </template>
          <template v-if="fileMetaModal.data?.pistes_sous_titres?.length">
            <div class="mm-info-section-title">
              <Captions :size="11" />
              {{
                $t('mediaManager.subtitleTracksWithCount', {
                  count: fileMetaModal.data.pistes_sous_titres.length,
                })
              }}
            </div>
            <div
              v-for="(t, ti) in fileMetaModal.data.pistes_sous_titres"
              :key="'s' + ti"
              class="mm-track-card"
              :class="{ 'mm-track-default': t.par_defaut }"
            >
              <div class="mm-track-badges">
                <span v-if="t.langue" class="mm-track-badge mm-badge-lang">{{ t.langue }}</span>
                <span v-if="t.codec" class="mm-track-badge mm-badge-dim">{{ t.codec }}</span>
                <span v-if="t.force" class="mm-track-badge mm-badge-warn">
                  {{ $t('mediaManager.trackForced') }}
                </span>
                <span v-if="t.malentendants" class="mm-track-badge mm-badge-dim">SDH</span>
                <span v-if="t.par_defaut" class="mm-track-badge mm-badge-default">
                  {{ $t('mediaManager.trackDefault') }}
                </span>
              </div>
              <div v-if="t.titre" class="mm-track-title">{{ t.titre }}</div>
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
import { useMediaManager } from '@/composables/useMediaManager'
import { Captions, FileText, Info, Video, Volume2 } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'
import { localizedDate } from '@/utils/datetime'

const { fileMetaModal, closeFileMeta } = useMediaManager()

const META_LABELS = {
  resolution: 'Resolution',
  source: 'Source',
  codec_video: 'Video codec',
  codec_audio: 'Audio codec',
  hdr: 'HDR',
  bit_depth: 'Bit depth',
  langues: 'Languages',
  sous_titres: 'Subtitles',
  annee: 'Year',
  episode: 'Episode',
  edition: 'Edition',
  qualite_note: 'Quality',
  team: 'Team / Group',
  framerate: 'FPS',
}
function metaKeyLabel(key) {
  return META_LABELS[key] || key
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
