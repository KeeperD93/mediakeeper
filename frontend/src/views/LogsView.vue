<template>
  <div class="cinema-logs mk-page-root">
    <div class="logs-content">
      <!-- TAB: Journaux -->
      <div v-show="activeTab === 'logs'">
        <template v-if="!currentFile">
          <div class="logs-header">
            <h2 class="logs-title">{{ $t('logs.tabLogs') }}</h2>
          </div>

          <div v-if="loadingFiles" class="logs-loading">
            <div v-for="i in 3" :key="i" class="logs-file-skel" />
          </div>

          <div v-else-if="!files.length" class="logs-empty">
            <p>{{ $t('logs.noFiles') }}</p>
          </div>

          <div v-else class="logs-files">
            <div
              v-for="f in files"
              :key="f.filename"
              class="logs-file-card"
              @click="viewFile(f.filename)"
            >
              <div
                class="file-icon"
                :class="f.filename.startsWith('emby') ? 'icon-emby' : 'icon-mk'"
              >
                <Film v-if="f.filename.startsWith('emby')" :size="16" />
                <FileText v-else :size="16" />
              </div>
              <div class="file-info">
                <span class="file-name">{{ f.filename }}</span>
                <span class="file-date">{{ f.modified_label }}</span>
              </div>
              <span class="file-size">{{ f.size_label }}</span>
              <button class="file-dl-btn" @click.stop="downloadFile(f.filename)">
                <Download class="w-4 h-4" />
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="reader-toolbar">
            <button class="logs-back-btn" @click="backToFiles">
              <ChevronLeft :size="14" />
              {{ $t('common.back') }}
            </button>
            <div class="reader-title">
              <span class="reader-filename">{{ currentFile }}</span>
              <span class="reader-status">{{ statusText }}</span>
            </div>
            <div class="reader-actions">
              <button
                class="reader-btn"
                :class="{ active: autoRefresh }"
                @click="toggleAutoRefresh"
              >
                <RefreshCw :size="13" />
                Auto {{ autoRefresh ? 'ON' : 'OFF' }}
              </button>
              <button class="reader-btn reader-btn-dl" @click="downloadFile(currentFile)">
                <Download :size="13" />
                {{ $t('common.download') }}
              </button>
            </div>
          </div>

          <div class="reader-filters">
            <div class="level-buttons">
              <button
                v-for="lvl in levels"
                :key="lvl.name"
                class="level-btn"
                :class="{ active: filters[lvl.name] }"
                :style="lvl.style"
                @click="filters[lvl.name] = !filters[lvl.name]"
              >
                {{ lvl.name }}
              </button>
            </div>
            <select v-model="filterModule" class="reader-search reader-search-sel">
              <option value="">{{ $t('logs.allModules') }}</option>
              <option v-for="m in detectedModules" :key="m" :value="m">{{ m }}</option>
            </select>
            <input
              v-model="search"
              type="text"
              :placeholder="$t('logs.searchPlaceholder')"
              class="reader-search"
            />
            <span class="reader-count">{{ countText }}</span>
          </div>

          <div ref="readerEl" class="reader-content">
            <div v-if="!rawLines.length" class="reader-empty">{{ $t('logs.fileEmpty') }}</div>
            <div v-else-if="!filteredLines.length" class="reader-empty">
              {{ $t('logs.noMatch') }}
            </div>
            <template v-else>
              <div
                v-for="(line, i) in displayLines"
                :key="i"
                class="log-line"
                :class="lineClass(line)"
              >
                <template v-for="(seg, j) in lineSegments(line)" :key="j">
                  <mark v-if="seg.highlight" class="log-highlight">{{ seg.text }}</mark>
                  <template v-else>{{ seg.text }}</template>
                </template>
              </div>
            </template>
          </div>
        </template>
      </div>

      <!-- TAB: Configuration -->
      <div v-show="activeTab === 'config'">
        <div class="logs-header">
          <h2 class="logs-title">{{ $t('logs.tabConfig') }}</h2>
        </div>

        <div class="glass-card logs-config-card">
          <section class="params-section">
            <h3 class="params-section-title">{{ $t('logs.debugMode') }}</h3>
            <p class="params-section-desc">{{ $t('logs.debugDesc') }}</p>
            <div class="params-toggle-row">
              <div>
                <span class="debug-status" :class="{ active: debugEnabled }">
                  {{ debugEnabled ? $t('logs.debugActive') : $t('logs.debugStandard') }}
                </span>
              </div>
              <label class="params-switch">
                <input type="checkbox" :checked="debugEnabled" @change="toggleDebug" />
                <span class="params-switch-slider" />
              </label>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useLogs } from '@/composables/useLogs'
import { useTabSync } from '@/composables/useTabSync'
import { ChevronLeft, Download, FileText, Film, RefreshCw } from 'lucide-vue-next'
import '@/assets/styles/logs-view.css'

const activeTab = useTabSync(['logs', 'config'], 'logs')
const readerEl = ref(null)

const {
  files,
  loadingFiles,
  debugEnabled,
  currentFile,
  rawLines,
  search,
  autoRefresh,
  filters,
  filterModule,
  detectedModules,
  filteredLines,
  displayLines,
  statusText,
  countText,
  lineClass,
  lineSegments,
  fetchFiles,
  loadDebugMode,
  toggleDebug,
  viewFile,
  backToFiles,
  downloadFile,
  toggleAutoRefresh,
} = useLogs()

const levels = [
  { name: 'INFO', style: { '--lvl': '#34d399', '--lvl-bg': 'rgba(52,211,153,.15)' } },
  { name: 'DEBUG', style: { '--lvl': '#60a5fa', '--lvl-bg': 'rgba(96,165,250,.15)' } },
  { name: 'WARNING', style: { '--lvl': '#fbbf24', '--lvl-bg': 'rgba(251,191,36,.15)' } },
  { name: 'ERROR', style: { '--lvl': '#f87171', '--lvl-bg': 'rgba(248,113,113,.15)' } },
  { name: 'CRITICAL', style: { '--lvl': '#ef4444', '--lvl-bg': 'rgba(239,68,68,.15)' } },
]

onMounted(() => {
  fetchFiles()
  loadDebugMode()
})
</script>
