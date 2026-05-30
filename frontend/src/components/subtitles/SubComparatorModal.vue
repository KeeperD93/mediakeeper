<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="visible" class="sub-modal-overlay mk-modal-sheet" @click.self="$emit('close')">
        <div class="sub-cmp-modal glass-card mk-modal-sheet-panel">
          <h3 class="sub-cmp-title">{{ $t('subtitles.comparator') }}</h3>

          <!-- Warning -->
          <div v-if="!result" class="sub-cmp-warn">
            <AlertCircle :size="14" />
            <span>{{ $t('subtitles.compareWarning') }}</span>
          </div>

          <!-- Selected files -->
          <div v-if="!result" class="sub-cmp-files">
            <div class="sub-cmp-file">
              <span class="sub-cmp-label">A</span>
              <span class="sub-cmp-name">{{ fileA?.file_name || '—' }}</span>
            </div>
            <div class="sub-cmp-file">
              <span class="sub-cmp-label">B</span>
              <span class="sub-cmp-name">{{ fileB?.file_name || '—' }}</span>
            </div>
          </div>

          <!-- Loading -->
          <div v-if="loading" class="sub-cmp-center"><span class="mk-spin mk-spin-20" /></div>

          <!-- Results -->
          <div v-else-if="result" class="sub-cmp-results">
            <table class="sub-cmp-table">
              <thead>
                <tr>
                  <th></th>
                  <th>A — {{ fileA?.file_name }}</th>
                  <th>B — {{ fileB?.file_name }}</th>
                  <th>{{ $t('subtitles.compare') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="sub-cmp-row-label">{{ $t('subtitles.lineCount') }}</td>
                  <td>{{ result.a.line_count }}</td>
                  <td>{{ result.b.line_count }}</td>
                  <td :class="result.diff.line_count_diff > 50 ? 'cmp-warn' : 'cmp-ok'">
                    {{ result.diff.line_count_diff > 0 ? '±' + result.diff.line_count_diff : '=' }}
                  </td>
                </tr>
                <tr>
                  <td class="sub-cmp-row-label">{{ $t('subtitles.durationCoverage') }}</td>
                  <td>{{ result.a.first_ts }} → {{ result.a.last_ts }}</td>
                  <td>{{ result.b.first_ts }} → {{ result.b.last_ts }}</td>
                  <td :class="result.diff.duration_diff_sec > 30 ? 'cmp-warn' : 'cmp-ok'">
                    {{
                      result.diff.duration_diff_sec > 0
                        ? '±' + result.diff.duration_diff_sec + 's'
                        : '='
                    }}
                  </td>
                </tr>
                <tr>
                  <td class="sub-cmp-row-label">{{ $t('subtitles.encoding') }}</td>
                  <td>{{ result.a.encoding }}</td>
                  <td>{{ result.b.encoding }}</td>
                  <td :class="result.diff.encoding_match ? 'cmp-ok' : 'cmp-warn'">
                    {{ result.diff.encoding_match ? '=' : '≠' }}
                  </td>
                </tr>
                <tr>
                  <td class="sub-cmp-row-label">{{ $t('subtitles.fileSize') }}</td>
                  <td>{{ formatSize(result.a.size) }}</td>
                  <td>{{ formatSize(result.b.size) }}</td>
                  <td>
                    {{ result.diff.size_diff > 0 ? '±' + formatSize(result.diff.size_diff) : '=' }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="sub-cmp-quota">
              {{ result.remaining_downloads }} {{ $t('subtitles.downloadsLeft') }}
            </div>
          </div>

          <!-- Error -->
          <div v-if="error" class="sub-cmp-error">{{ error }}</div>

          <!-- Actions -->
          <div class="sub-cmp-actions">
            <button class="sub-modal-cancel" @click="$emit('close')">
              {{ $t('common.close') }}
            </button>
            <button v-if="!result && !loading" class="sub-modal-save" @click="doCompare">
              {{ $t('subtitles.compare') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { AlertCircle } from 'lucide-vue-next'

const props = defineProps({
  visible: Boolean,
  fileA: { type: Object, default: null },
  fileB: { type: Object, default: null },
})
defineEmits(['close'])

const { t } = useI18n()
const { apiPost } = useApi()
const loading = ref(false)
const result = ref(null)
const error = ref('')

async function doCompare() {
  if (!props.fileA || !props.fileB) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const d = await apiPost('/api/subtitles/compare', {
      file_id_a: props.fileA.file_id,
      file_id_b: props.fileB.file_id,
    })
    if (d && d.error) {
      error.value = d.error
    } else {
      result.value = d
    }
  } catch {
    error.value = t('subtitles.compareFailed')
  }
  loading.value = false
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  return (bytes / 1024).toFixed(1) + ' KB'
}
</script>

<style scoped>
.sub-modal-overlay {
  z-index: 1000;
}
@media (min-width: 768px) {
  .sub-cmp-modal {
    width: 600px;
    padding: 22px;
  }
}
.sub-cmp-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 14px;
}

.sub-cmp-warn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  border-radius: var(--radius-btn);
  font-size: var(--text-2xs);
  background: rgb(var(--color-warning-rgb), 0.08);
  border: 0.5px solid rgb(var(--color-warning-rgb), 0.15);
  color: var(--color-warning);
}

.sub-cmp-files {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}
.sub-cmp-file {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: rgb(255, 255, 255, 0.02);
  border-radius: var(--radius-btn);
}
.sub-cmp-label {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  color: var(--accent-400);
  min-width: 16px;
}
.sub-cmp-name {
  font-size: var(--text-2xs);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sub-cmp-center {
  display: flex;
  justify-content: center;
  padding: 30px;
}

.sub-cmp-results {
  overflow-x: auto;}
.sub-cmp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-2xs);
}
@media (max-width: 767px) {
  .sub-cmp-table {
    min-width: 520px;
  }
}
.sub-cmp-table th {
  text-align: left;
  padding: 6px 8px;
  color: var(--text-muted);
  font-weight: var(--font-medium);
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 0.5px solid var(--border-default);
}
.sub-cmp-table td {
  padding: 8px;
  color: var(--text-secondary);
  border-bottom: 0.5px solid rgb(255, 255, 255, 0.03);
}
.sub-cmp-row-label {
  font-weight: var(--font-medium);
  color: var(--text-muted);
  font-size: var(--text-2xs);
}
.cmp-ok {
  color: var(--color-success);
}
.cmp-warn {
  color: var(--color-warning);
}

.sub-cmp-quota {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  margin-top: 10px;
  text-align: right;
}
.sub-cmp-error {
  font-size: var(--text-2xs);
  color: #f43f5e;
  margin: 10px 0;
}

.sub-cmp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}
.sub-modal-cancel,
.sub-modal-save {
  padding: 7px 16px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.sub-modal-cancel {
  background: var(--surface-2);
  color: var(--text-secondary);
}
.sub-modal-save {
  background: var(--accent-500);
  color: var(--text-primary);
}
.sub-modal-save:hover {
  opacity: 0.9;
}

.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.sub-fade-enter-active,
.sub-fade-leave-active {
  transition: opacity var(--duration-base);
}
.sub-fade-enter-from,
.sub-fade-leave-to {
  opacity: 0;
}
</style>
