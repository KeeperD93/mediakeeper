<template>
  <div class="cinema-cl mk-page-root">
    <div class="cl-inner">
      <div class="cl-header">
        <div class="cl-title-row">
          <h1 class="cl-title">{{ $t('changelog.title') }}</h1>
          <span class="cl-current">v{{ currentVersion }}</span>
        </div>
        <p class="cl-subtitle">{{ $t('changelog.subtitle') }}</p>
      </div>

      <div v-if="loading" class="cl-loading">
        <MkSpinner size="md" />
      </div>

      <div v-else class="cl-timeline">
        <div
          v-for="(v, idx) in versions"
          :key="v.version"
          class="cl-version"
          :class="{ 'cl-latest': idx === 0 }"
        >
          <div class="cl-version-dot" :class="{ 'dot-latest': idx === 0 }" />
          <div class="cl-version-card">
            <div class="cl-version-header">
              <span class="cl-version-tag">v{{ v.version }}</span>
              <span v-if="idx === 0" class="cl-badge-latest">{{ $t('changelog.latest') }}</span>
              <span class="cl-version-date">{{ formatDate(v.date) }}</span>
            </div>
            <div v-for="surface in nonEmptySurfaces(v)" :key="surface" class="cl-surface">
              <div class="cl-surface-label">{{ $t('changelog.surface.' + surface) }}</div>
              <div
                v-for="(items, cat) in v[surface]"
                :key="surface + '-' + cat"
                class="cl-category"
              >
                <div class="cl-cat-header">
                  <span class="cl-cat-icon">{{ categoryIcon(cat) }}</span>
                  <span class="cl-cat-label" :class="'cat-' + categoryClass(cat)">
                    {{ $t('changelog.cat.' + categoryClass(cat)) }}
                  </span>
                </div>
                <ul class="cl-items">
                  <li v-for="(item, i) in items" :key="i" class="cl-item">{{ item }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import MkSpinner from '@/components/common/MkSpinner.vue'

const { locale } = useI18n()
const { apiGet, apiPost } = useApi()

const versions = ref([])
const currentVersion = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await apiGet(`/api/changelog/combined?lang=${locale.value}`)
    if (data) {
      versions.value = data.versions || []
      currentVersion.value = data.app_version || ''
    }
  } catch (e) {
    console.error('[Changelog] fetch error:', e)
  }
  loading.value = false

  // Mark both surfaces as seen — the admin viewing this page has now read
  // the merged timeline, so they should not be re-prompted by the modal.
  try {
    await apiPost('/api/changelog/combined/seen', {})
  } catch {
    /* silent: seen-marker is best-effort, no user-visible impact */
  }
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })
}

function categoryIcon(cat) {
  const map = { Added: '✨', Fixed: '🔧', Changed: '🔄', Removed: '🗑️' }
  return map[cat] || '📋'
}

function categoryClass(cat) {
  return (cat || '').toLowerCase()
}

// Filter out surfaces with no category entries so the section header
// (e.g. "User portal") is not rendered above an empty body when the
// release ships nothing on that surface.
function nonEmptySurfaces(version) {
  return ['admin', 'portal'].filter(surface => {
    const bucket = version?.[surface]
    return bucket && typeof bucket === 'object' && Object.keys(bucket).length > 0
  })
}
</script>

<style scoped>
.cinema-cl {
  position: relative;
  min-height: 100%;
  padding: 12px 24px 48px;
  overflow: hidden;
}

.cl-inner {
  position: relative;
  z-index: 1;
  max-width: 720px;
  margin: 0 auto;
}

.cl-header {
  margin-bottom: 32px;
}
.cl-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.cl-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0;
}
.cl-current {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  padding: 3px 10px;
  border-radius: var(--radius-btn);
  background: rgb(var(--accent-rgb), 0.12);
  color: var(--accent-400);
  font-family: 'SF Mono', 'Cascadia Mono', monospace;
}
.cl-subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-top: 6px;
}

.cl-loading {
  display: flex;
  justify-content: center;
  padding: 60px;
}

/* Timeline */
.cl-timeline {
  position: relative;
  padding-left: 24px;
}
.cl-timeline::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 8px;
  bottom: 0;
  width: 1px;
  background: linear-gradient(to bottom, rgb(var(--accent-rgb), 0.3), rgb(var(--accent-rgb), 0.05));
}

.cl-version {
  position: relative;
  margin-bottom: 28px;
}
.cl-version-dot {
  position: absolute;
  left: -24px;
  top: 10px;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgb(var(--accent-rgb), 0.3);
  background: var(--bg-primary);
  z-index: 1;
  transition: all var(--duration-base);
}
.cl-version:hover .cl-version-dot {
  border-color: var(--accent-500);
}
.dot-latest {
  background: var(--accent-500);
  border-color: var(--accent-500);
  box-shadow: 0 0 12px rgb(var(--accent-rgb), 0.4);
}

.cl-version-card {
  background: rgb(255, 255, 255, 0.02);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  transition: border-color var(--duration-base);
}
.cl-version:hover .cl-version-card {
  border-color: rgb(var(--accent-rgb), 0.15);
}
.cl-latest .cl-version-card {
  border-color: rgb(var(--accent-rgb), 0.2);
  background: rgb(var(--accent-rgb), 0.03);
}

.cl-version-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.cl-version-tag {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  font-family: 'SF Mono', 'Cascadia Mono', monospace;
}
.cl-badge-latest {
  font-size: 0.58rem;
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: rgb(var(--color-success-rgb), 0.12);
  color: var(--color-success);
}
.cl-version-date {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-left: auto;
}

.cl-surface {
  margin-top: 22px;
  padding-top: 16px;
  border-top: 0.5px solid var(--border-subtle);
}
.cl-surface:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}
.cl-surface-label {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--accent-400);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  margin: 0 0 12px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: rgb(var(--accent-rgb), 0.08);
}

.cl-category {
  margin-bottom: 12px;
}
.cl-category:last-child {
  margin-bottom: 0;
}
.cl-cat-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.cl-cat-icon {
  font-size: var(--text-sm);
}
.cl-cat-label {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
}
.cat-added {
  color: var(--color-success);
}
.cat-fixed {
  color: var(--color-info);
}
.cat-changed {
  color: var(--color-warning);
}
.cat-removed {
  color: var(--color-error);
}

.cl-items {
  list-style: none;
  padding: 0;
  margin: 0;
}
.cl-item {
  position: relative;
  padding: 3px 0 3px 16px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.55;
}
.cl-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 11px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgb(255, 255, 255, 0.12);
}

@media (max-width: 768px) {
  .cinema-cl {
    padding: 12px 16px 32px;
  }
  .cl-version-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .cl-version-date {
    margin-left: 0;
  }
}
</style>
