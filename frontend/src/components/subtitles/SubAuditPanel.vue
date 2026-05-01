<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="visible" class="sub-modal-overlay" @click.self="$emit('close')">
        <div class="sub-audit-modal">
          <h3 class="sub-audit-title">{{ $t('subtitles.audit') }}</h3>

          <!-- Config -->
          <div v-if="!results && !running" class="sub-audit-config">
            <div class="sub-audit-field">
              <label>{{ $t('subtitles.languages') }}</label>
              <div class="sub-audit-checks">
                <label><input v-model="langs" type="checkbox" value="fre" /> FR</label>
                <label><input v-model="langs" type="checkbox" value="eng" /> EN</label>
                <label><input v-model="langs" type="checkbox" value="spa" /> ES</label>
                <label><input v-model="langs" type="checkbox" value="ger" /> DE</label>
              </div>
            </div>
            <div class="sub-audit-field">
              <label>{{ $t('subtitles.auditChecks') }}</label>
              <div class="sub-audit-checks">
                <label><input v-model="checks" type="checkbox" value="missing" /> {{ $t('subtitles.filterMissing') }}</label>
                <label><input v-model="checks" type="checkbox" value="forced" /> {{ $t('subtitles.missingForced') }}</label>
                <label><input v-model="checks" type="checkbox" value="image_only" /> {{ $t('subtitles.imageOnlySubs') }}</label>
                <label><input v-model="checks" type="checkbox" value="encoding" /> {{ $t('subtitles.encodingIssues') }}</label>
              </div>
            </div>
            <button class="sub-audit-start" :disabled="!langs.length || !checks.length" @click="startAudit">
              {{ $t('subtitles.startAudit') }}
            </button>
          </div>

          <!-- Progress -->
          <div v-if="running" class="sub-audit-progress">
            <div class="sub-audit-bar-wrap">
              <div class="sub-audit-bar">
                <div class="sub-audit-fill" :style="{ width: pct + '%' }" />
              </div>
              <span class="sub-audit-pct">{{ progress.current }}/{{ progress.total }}</span>
            </div>
            <div class="sub-audit-label">{{ progress.label }}</div>
          </div>

          <!-- Results -->
          <div v-if="results" class="sub-audit-results">
            <!-- Summary -->
            <div class="sub-audit-summary">
              <div v-for="(count, lang) in (results.summary?.missing || {})" :key="'miss-'+lang" class="sub-audit-sum-card">
                <span class="sub-audit-sum-val">{{ count }}</span>
                <span class="sub-audit-sum-label">{{ $t('subtitles.filterMissing') }} {{ lang.toUpperCase() }}</span>
              </div>
              <div v-if="results.summary?.image_only" class="sub-audit-sum-card">
                <span class="sub-audit-sum-val">{{ results.summary.image_only }}</span>
                <span class="sub-audit-sum-label">{{ $t('subtitles.imageOnlySubs') }}</span>
              </div>
              <div v-if="results.summary?.missing_forced" class="sub-audit-sum-card">
                <span class="sub-audit-sum-val">{{ results.summary.missing_forced }}</span>
                <span class="sub-audit-sum-label">{{ $t('subtitles.missingForced') }}</span>
              </div>
              <div v-if="results.summary?.encoding_issues" class="sub-audit-sum-card">
                <span class="sub-audit-sum-val">{{ results.summary.encoding_issues }}</span>
                <span class="sub-audit-sum-label">{{ $t('subtitles.encodingIssues') }}</span>
              </div>
            </div>

            <!-- Items list -->
            <div class="sub-audit-list">
              <div v-for="item in (results.items || []).slice(0, 100)" :key="item.item_id" class="sub-audit-item">
                <div class="sub-audit-item-info">
                  <span class="sub-audit-item-name">{{ item.series_name ? item.series_name + ' — ' : '' }}{{ item.name }}</span>
                  <span class="sub-audit-item-type">{{ item.type }}</span>
                </div>
                <div class="sub-audit-item-issues">
                  <span v-for="issue in item.issues" :key="issue" class="sub-audit-issue" :class="issueClass(issue)">{{ issueLabel(issue) }}</span>
                </div>
              </div>
              <div v-if="(results.items || []).length > 100" class="sub-audit-more">
                +{{ (results.items || []).length - 100 }} {{ $t('subtitles.loadMore') }}
              </div>
            </div>

            <!-- Actions -->
            <button class="sub-audit-restart" @click="results = null">{{ $t('subtitles.startAudit') }}</button>
          </div>

          <div class="sub-audit-close">
            <button class="sub-modal-cancel" @click="$emit('close')">{{ $t('common.close') }}</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useSubtitles } from '@/composables/useSubtitles'
import { SUB_LIB_STATUS } from '@/constants/subtitles'

defineProps({ visible: Boolean })
const emit = defineEmits(['close'])

const { apiPost, apiGet } = useApi()
const { defaultLanguages } = useSubtitles()

const langs = ref([...defaultLanguages.value])
const checks = ref(['missing', 'forced', 'image_only'])
const running = ref(false)
const progress = ref({ current: 0, total: 0, label: '' })
const results = ref(null)
let _timer = null

const pct = computed(() => {
  if (!progress.value.total) return 0
  return Math.round((progress.value.current / progress.value.total) * 100)
})

async function startAudit() {
  running.value = true
  results.value = null
  try {
    await apiPost('/api/subtitles/audit', {
      languages: langs.value,
      checks: checks.value,
    })
    // Poll progress
    _timer = setInterval(async () => {
      try {
        const p = await apiGet('/api/subtitles/audit-progress')
        if (p) progress.value = p
        if (!p.running) {
          clearInterval(_timer)
          running.value = false
          const r = await apiGet('/api/subtitles/audit-results')
          if (r) results.value = r
        }
      } catch { /* silent: audit progress poll, retries next tick */ }
    }, 2000)
  } catch {
    running.value = false
  }
}

function issueClass(issue) {
  if (issue.startsWith('missing_')) return 'issue-missing'
  if (issue === SUB_LIB_STATUS.IMAGE_ONLY) return 'issue-image'
  if (issue === 'missing_forced') return 'issue-forced'
  if (issue.startsWith('encoding:')) return 'issue-encoding'
  return ''
}

function issueLabel(issue) {
  if (issue.startsWith('missing_')) return '⊘ ' + issue.replace('missing_', '').toUpperCase()
  if (issue === SUB_LIB_STATUS.IMAGE_ONLY) return 'PGS only'
  if (issue === 'missing_forced') return 'No forced'
  if (issue.startsWith('encoding:')) return issue.replace('encoding:', '')
  return issue
}

onUnmounted(() => {
  clearInterval(_timer)
})
</script>

<style scoped>
.sub-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.sub-audit-modal {
  width: 640px; max-width: 95vw; max-height: 85vh; overflow-y: auto; padding: 22px;
  border-radius: var(--radius-card);
  background: var(--bg-secondary); border: 1px solid var(--border-strong);
}
.sub-audit-title { font-size: var(--text-base); font-weight: var(--font-medium); color: var(--text-primary); margin: 0 0 16px; }

.sub-audit-config { }
.sub-audit-field { margin-bottom: 12px; }
.sub-audit-field > label { display: block; font-size: var(--text-2xs); color: var(--text-muted); margin-bottom: 6px; font-weight: var(--font-medium); }
.sub-audit-checks { display: flex; flex-wrap: wrap; gap: 10px; }
.sub-audit-checks label { display: flex; align-items: center; gap: 4px; font-size: var(--text-2xs); color: var(--text-secondary); cursor: pointer; }
.sub-audit-start {
  padding: 8px 20px; border-radius: var(--radius-btn); font-size: var(--text-xs); font-weight: var(--font-medium);
  background: var(--accent-500); color: #fff; border: none; cursor: pointer; font-family: inherit;
}
.sub-audit-start:disabled { opacity: .4; cursor: default; }

.sub-audit-progress { padding: 16px 0; }
.sub-audit-bar-wrap { display: flex; align-items: center; gap: 8px; }
.sub-audit-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.sub-audit-fill { height: 100%; border-radius: 3px; background: var(--accent-500); transition: width var(--duration-slow); }
.sub-audit-pct { font-size: var(--text-3xs); color: var(--text-muted); }
.sub-audit-label { font-size: var(--text-2xs); color: var(--text-muted); margin-top: 6px; }

.sub-audit-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 6px; margin-bottom: 14px; }
.sub-audit-sum-card { display: flex; flex-direction: column; align-items: center; padding: 10px 8px; background: rgba(255,255,255,.02); border-radius: var(--radius-btn); gap: 2px; }
.sub-audit-sum-val { font-size: var(--text-md); font-weight: var(--font-bold); color: #fb7185; }
.sub-audit-sum-label { font-size: .55rem; color: var(--text-muted); text-align: center; }

.sub-audit-list { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 3px; }
.sub-audit-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 8px; background: rgba(255,255,255,.02); border-radius: var(--radius-btn); }
.sub-audit-item-info { flex: 1; min-width: 0; }
.sub-audit-item-name { display: block; font-size: var(--text-2xs); color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub-audit-item-type { font-size: .55rem; color: var(--text-muted); }
.sub-audit-item-issues { display: flex; gap: 4px; flex-wrap: wrap; flex-shrink: 0; }
.sub-audit-issue { font-size: .5rem; padding: 1px 5px; border-radius: 3px; font-weight: var(--font-medium); }
.issue-missing { background: rgba(244,63,94,.12); color: #f43f5e; }
.issue-image { background: rgba(var(--color-warning-rgb),.12); color: var(--color-warning); }
.issue-forced { background: rgba(168,85,247,.12); color: #a855f7; }
.issue-encoding { background: rgba(var(--color-info-rgb),.12); color: var(--color-info); }

.sub-audit-more { font-size: var(--text-3xs); color: var(--text-muted); text-align: center; padding: 8px; }
.sub-audit-restart {
  margin-top: 12px; padding: 7px 16px; border-radius: var(--radius-btn); font-size: var(--text-2xs);
  background: rgba(var(--accent-rgb),.12); color: var(--accent-400);
  border: .5px solid rgba(var(--accent-rgb),.2); cursor: pointer; font-family: inherit;
}
.sub-audit-close { display: flex; justify-content: flex-end; margin-top: 14px; border-top: .5px solid var(--border-default); padding-top: 12px; }
.sub-modal-cancel {
  padding: 7px 16px; border-radius: var(--radius-btn); font-size: var(--text-xs); font-weight: var(--font-regular);
  border: none; cursor: pointer; font-family: inherit;
  background: var(--surface-2); color: var(--text-secondary);
}

.sub-fade-enter-active, .sub-fade-leave-active { transition: opacity var(--duration-base); }
.sub-fade-enter-from, .sub-fade-leave-to { opacity: 0; }
</style>
