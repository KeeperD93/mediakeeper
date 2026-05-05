<template>
  <div class="tab-panel">
    <div class="tools-grid">
      <div class="glass-card tool-card">
        <div class="tool-head">
          <Upload :size="18" class="tool-ico-accent" />
          <h3 class="tool-title">{{ $t('stats.importJellystats') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.importBackupDesc') }}</p>
        <label class="tool-btn-accent">
          <Plus :size="14" />
          {{ $t('stats.chooseFile') }}
          <input type="file" accept=".json" class="tool-file-hidden" @change="importJellystats" />
        </label>
        <div v-if="importStatus" class="tool-status" :class="importStatus.type">
          {{ importStatus.text }}
        </div>
      </div>
      <div class="glass-card tool-card">
        <div class="tool-head">
          <Trash2 :size="18" class="tool-ico-danger" />
          <h3 class="tool-title">{{ $t('stats.purge') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.purgeDesc') }}</p>
        <button class="tool-btn-danger" @click="purgeJellystats">
          <Trash2 :size="14" />
          {{ $t('stats.purgeBtn') }}
        </button>
        <div v-if="purgeStatus" class="tool-status" :class="purgeStatus.type">
          {{ purgeStatus.text }}
        </div>
      </div>
      <div class="glass-card tool-card">
        <div class="tool-head">
          <RefreshCw :size="18" class="tool-ico-accent" />
          <h3 class="tool-title">{{ $t('stats.migration') }}</h3>
        </div>
        <p class="tool-desc">{{ $t('stats.migrationDesc') }}</p>
        <button class="tool-btn-accent" @click="migrateLibNames">
          <RotateCw :size="14" />
          {{ $t('stats.launch') }}
        </button>
        <div v-if="migrateStatus" class="tool-status" :class="migrateStatus.type">
          {{ migrateStatus.text }}
        </div>
      </div>
    </div>
    <div class="glass-card tool-card tool-card-excl">
      <div class="tool-head">
        <Ban :size="18" class="tool-ico-accent" />
        <h3 class="tool-title">{{ $t('stats.exclusions') }}</h3>
      </div>
      <p class="tool-desc">{{ $t('stats.exclusionsDesc') }}</p>
      <div class="excl-add">
        <select v-model="exclMode" class="excl-sel">
          <option value="exact">{{ $t('stats.exact') }}</option>
          <option value="contains">{{ $t('stats.contains') }}</option>
        </select>
        <input
          v-model="exclValue"
          class="excl-input"
          :placeholder="$t('stats.titlePlaceholder')"
          @keydown.enter="addExclusion"
        />
        <button class="excl-add-btn" @click="addExclusion"><Plus :size="14" /></button>
      </div>
      <div v-if="!exclusions.length" class="excl-empty">{{ $t('stats.noExclusions') }}</div>
      <div v-for="(exc, i) in exclusions" :key="i" class="excl-item">
        <span class="excl-badge">
          {{ exc.mode === 'exact' ? $t('stats.exact') : $t('stats.contains') }}
        </span>
        <span class="excl-val">{{ exc.value }}</span>
        <button class="excl-rm" @click="removeExclusion(i)">
          <X :size="10" :stroke-width="2.5" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useStats } from '@/composables/useStats'
import { Ban, Plus, RefreshCw, RotateCw, Trash2, Upload, X } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

const { t } = useI18n()
const { apiFetch, apiGet, apiPost, apiDelete } = useApi()
const { loadTotals } = useStats()

const importStatus = ref(null)
const purgeStatus = ref(null)
const migrateStatus = ref(null)
const exclusions = ref([])
const exclMode = ref('exact')
const exclValue = ref('')

async function importJellystats(e) {
  const f = e.target.files[0]
  if (!f) return
  importStatus.value = { type: 'info', text: t('stats.import') + '...' }
  try {
    const fd = new FormData()
    fd.append('file', f)
    const r = await apiFetch('/api/stats/import/jellystats', { method: 'POST', body: fd })
    const d = r ? await r.json() : {}
    if (d.error) importStatus.value = { type: 'err', text: d.error }
    else {
      importStatus.value = {
        type: 'ok',
        text: `${d.playback_imported} ${t('stats.imported')}, ${d.playback_skipped} ${t('stats.duplicatesSkipped')}`,
      }
      loadTotals()
    }
  } catch {
    importStatus.value = { type: 'err', text: t('common.error') }
  }
  e.target.value = ''
}

async function purgeJellystats() {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('stats.purgeConfirm'),
    variant: 'danger',
  })
  if (!ok) return
  purgeStatus.value = { type: 'info', text: t('stats.purgeBtn') + '...' }
  try {
    const d = await apiPost('/api/stats/import/jellystats/purge')
    purgeStatus.value = { type: 'ok', text: `${d.total_purged} ${t('stats.purged')}` }
    loadTotals()
  } catch {
    purgeStatus.value = { type: 'err', text: t('common.error') }
  }
}

async function migrateLibNames() {
  migrateStatus.value = { type: 'info', text: t('stats.migration') + '...' }
  try {
    const d = await apiPost('/api/stats/migrate/library-names')
    if (d.error) {
      migrateStatus.value = { type: 'err', text: d.error }
      return
    }
    migrateStatus.value = {
      type: 'ok',
      text: `${d.migrated} ${t('stats.resolved')}, ${d.fallback} ${t('stats.fallback')}`,
    }
  } catch {
    migrateStatus.value = { type: 'err', text: t('common.error') }
  }
}

async function loadExclusions() {
  try {
    const d = await apiGet('/api/stats/exclusions')
    if (Array.isArray(d)) exclusions.value = d
  } catch {
    /* silent: exclusions fetch */
  }
}

async function addExclusion() {
  const v = exclValue.value.trim()
  if (!v) return
  try {
    await apiPost('/api/stats/exclusions', { mode: exclMode.value, value: v })
    exclValue.value = ''
    loadExclusions()
    loadTotals()
  } catch (e) {
    console.error('[StatsToolsTab.addExclusion] failed to add exclusion', e)
  }
}

async function removeExclusion(i) {
  try {
    await apiDelete(`/api/stats/exclusions/${i}`)
    loadExclusions()
    loadTotals()
  } catch (e) {
    console.error('[StatsToolsTab.removeExclusion] failed to remove exclusion', e)
  }
}

onMounted(() => {
  if (!exclusions.value.length) loadExclusions()
})
</script>

<style scoped>
.tools-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.tool-card {
  padding: 18px 20px;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.tool-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.tool-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0;
}
.tool-desc {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  margin-bottom: 14px;
  line-height: var(--lh-normal);
}
.tool-btn-accent {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-400);
  border: 0.5px solid rgb(var(--accent-rgb), 0.2);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.tool-btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  background: rgb(239, 68, 68, 0.1);
  color: var(--color-error);
  border: 0.5px solid rgb(239, 68, 68, 0.15);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.tool-status {
  margin-top: 10px;
  font-size: var(--text-2xs);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
}
.tool-status.info {
  background: rgb(var(--accent-rgb), 0.1);
  color: var(--accent-400);
}
.tool-status.ok {
  background: rgb(34, 197, 94, 0.1);
  color: var(--color-success);
}
.tool-status.err {
  background: rgb(239, 68, 68, 0.1);
  color: var(--color-error);
}

.excl-add {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}
.excl-sel {
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 5px 8px;
  font-size: var(--text-2xs);
  color: var(--text-primary);
  outline: none;
  width: 80px;
}
.excl-input {
  flex: 1;
  min-width: 0;
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 5px 10px;
  font-size: var(--text-2xs);
  color: var(--text-primary);
  outline: none;
}
.excl-input:focus {
  border-color: var(--accent-500);
}
.excl-add-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-400);
  border: 0.5px solid rgb(var(--accent-rgb), 0.2);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.excl-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: 4px 0;
}
.excl-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 6px;
  border-radius: var(--radius-sm);
}
.excl-badge {
  font-size: 0.58rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--text-muted);
  flex-shrink: 0;
}
.excl-val {
  flex: 1;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.excl-rm {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: #ef4444;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  opacity: 0.4;
}

.tool-ico-accent {
  color: var(--accent-500);
}
.tool-ico-danger {
  color: var(--color-error);
}
.tool-file-hidden {
  display: none;
}
.tool-card-excl {
  margin-top: 14px;
}
@media (max-width: 1280px) {
  .tools-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .tools-grid {
    grid-template-columns: 1fr;
  }
}
@media (hover: hover) {
  .tool-btn-accent:hover,
  .excl-add-btn:hover {
    background: rgb(var(--accent-rgb), 0.25);
  }
  .tool-btn-danger:hover {
    background: rgb(239, 68, 68, 0.2);
  }
  .excl-item:hover {
    background: rgb(255, 255, 255, 0.03);
  }
  .excl-rm:hover {
    opacity: 1;
  }
}
</style>
