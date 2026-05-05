<template>
  <section class="ale">
    <header v-if="lst.description" class="ale-desc">{{ lst.description }}</header>

    <div class="ale-cols">
      <!-- Items column -->
      <div class="ale-col ale-col--items">
        <div class="ale-col-head">
          <h4>{{ $t('portal.lists.form.name') }}</h4>
          <span class="ale-count">{{ detail?.items_total || 0 }}</span>
        </div>
        <div v-if="loadingItems" class="ale-loading"><MkSpinner size="md" /></div>
        <div v-else-if="!detail?.items?.length" class="ale-empty">—</div>
        <ul v-else class="ale-items">
          <li v-for="item in detail.items" :key="item.id" class="ale-item">
            <router-link
              :to="{
                name: 'portal-media-detail',
                params: { type: item.media_type, id: item.tmdb_id },
              }"
              class="ale-item-link"
            >
              <span class="ale-item-poster">
                <img
                  v-if="item.poster_url"
                  :src="item.poster_url"
                  :alt="item.title || ''"
                  loading="lazy"
                />
                <span v-else class="ale-item-poster-fallback">
                  {{ (item.title || '?').charAt(0) }}
                </span>
              </span>
              <span class="ale-item-main">
                <span class="ale-item-title-row">
                  <span class="ale-item-title">{{ item.title || `#${item.tmdb_id}` }}</span>
                  <button
                    type="button"
                    class="ale-item-copy"
                    :title="copiedId === item.id ? $t('common.copied') : $t('common.copy')"
                    :aria-label="$t('common.copy')"
                    @click.prevent.stop="copyTitle(item)"
                  >
                    <Copy v-if="copiedId !== item.id" :size="14" :stroke-width="2.2" />
                    <Check v-else :size="14" :stroke-width="2.5" />
                  </button>
                </span>
                <span class="ale-item-meta">
                  <span class="ale-item-type">{{ item.media_type }}</span>
                  <span v-if="item.year" class="ale-item-year">{{ item.year }}</span>
                  <span class="ale-item-id">#{{ item.tmdb_id }}</span>
                </span>
              </span>
              <span class="ale-item-date">{{ formatDate(item.added_at) }}</span>
            </router-link>
            <button
              v-if="canEdit"
              class="ale-item-remove"
              type="button"
              :title="$t('common.delete')"
              :aria-label="$t('common.delete')"
              @click="$emit('remove-item', item.id)"
            >
              <X :size="14" :stroke-width="2.2" />
            </button>
          </li>
        </ul>
      </div>

      <!-- Contributors + history column -->
      <aside v-if="lst.privacy !== 'private'" class="ale-col ale-col--side">
        <div class="ale-side-block">
          <div class="ale-col-head">
            <h4>{{ $t('portal.lists.contributors') }}</h4>
          </div>
          <ul v-if="allContributors.length" class="ale-contributors">
            <li v-for="c in allContributors" :key="c.user_id" class="ale-contrib">
              <span class="ale-contrib-avatar">
                {{ (c.username || '?').charAt(0).toUpperCase() }}
              </span>
              <span class="ale-contrib-name">{{ c.username || `#${c.user_id}` }}</span>
              <span v-if="c.is_owner_row" class="ale-contrib-owner">
                {{ $t('portal.lists.ownerBadge') }}
              </span>
              <span
                v-if="c.muted"
                class="ale-contrib-muted"
                :title="$t('portal.lists.errors.contributor_muted')"
              >
                🔇
              </span>
              <button
                v-if="lst.is_owner && !c.is_owner_row"
                class="ale-contrib-remove"
                type="button"
                :title="$t('common.delete')"
                @click="$emit('remove-contributor', c.user_id)"
              >
                ✕
              </button>
            </li>
          </ul>
          <p v-else class="ale-empty">—</p>
        </div>

        <div class="ale-side-block">
          <button
            type="button"
            class="ale-history-toggle"
            :aria-expanded="historyOpen"
            @click="historyOpen = !historyOpen"
          >
            <span class="ale-history-toggle-label">{{ $t('portal.lists.history.title') }}</span>
            <span v-if="history.length" class="ale-history-toggle-count">{{ history.length }}</span>
            <ChevronDown
              class="ale-history-toggle-chev"
              :class="{ 'ale-history-toggle-chev--open': historyOpen }"
              :size="14"
              :stroke-width="2.4"
            />
          </button>
          <template v-if="historyOpen">
            <div v-if="loadingHistory" class="ale-loading"><MkSpinner size="md" /></div>
            <ul v-else-if="history.length" class="ale-history">
              <li v-for="h in history" :key="h.id" class="ale-event">
                <span v-if="h.username" class="ale-event-who">{{ h.username }}</span>
                <span class="ale-event-action" :class="`ale-event--${h.action}`">
                  {{ actionLabel(h) }}
                </span>
                <span class="ale-event-date">{{ formatDate(h.created_at) }}</span>
              </li>
            </ul>
            <p v-else class="ale-empty">—</p>
          </template>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalLists } from '@/composables/portal/usePortalLists'
import { Check, ChevronDown, Copy, X } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'

const props = defineProps({
  lst: { type: Object, required: true },
})
defineEmits(['remove-item', 'remove-contributor'])

const { t } = useI18n()
const svc = usePortalLists()

const detail = ref(null)
const contributors = ref([])
const history = ref([])
const loadingItems = ref(false)
const loadingHistory = ref(false)
const historyOpen = ref(false)
const copiedId = ref(null)

async function copyTitle(item) {
  const text = item.title || `#${item.tmdb_id}`
  try {
    await navigator.clipboard?.writeText(text)
    copiedId.value = item.id
    setTimeout(() => {
      if (copiedId.value === item.id) copiedId.value = null
    }, 1600)
  } catch {
    /* silent */
  }
}

const canEdit = computed(() => props.lst.is_owner)

// Owner is implicit in the DB — prepend as synthetic row.
const allContributors = computed(() => {
  const owner = {
    user_id: props.lst.owner_id,
    username: props.lst.owner_username || detail.value?.owner_username,
    muted: props.lst.owner_muted,
    is_owner_row: true,
  }
  return [owner, ...contributors.value.filter(c => c.user_id !== owner.user_id)]
})

async function load() {
  loadingItems.value = true
  try {
    const d = await svc.fetchList(props.lst.id, { pageSize: 50 })
    if (d && !d.error) {
      detail.value = d
      contributors.value = d.contributors || []
    }
  } finally {
    loadingItems.value = false
  }

  if (props.lst.privacy !== 'private') {
    loadingHistory.value = true
    try {
      const hist = await svc.fetchHistory(props.lst.id, 20)
      history.value = hist || []
    } finally {
      loadingHistory.value = false
    }
  }
}

watch(() => props.lst.id, load, { immediate: true })

defineExpose({ reload: load })

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString()
}

function actionLabel(h) {
  const title = h.title || (h.tmdb_id ? `#${h.tmdb_id}` : '')
  const map = {
    created: t('portal.lists.history.created'),
    added: t('portal.lists.history.added', { title }),
    removed: t('portal.lists.history.removed', { title }),
    copied: t('portal.lists.history.copied'),
    updated: t('portal.lists.history.updated'),
    deleted: t('portal.lists.history.deleted'),
    contributor_added: t('portal.lists.history.contributorAdded'),
    contributor_removed: t('portal.lists.history.contributorRemoved'),
  }
  return map[h.action] || h.action
}
</script>

<style scoped>
.ale {
  position: relative;
  z-index: 1;
  margin: -10px 0 6px;
  padding: 18px 22px 20px;
  background: linear-gradient(180deg, var(--portal-surface-1), rgb(255, 255, 255, 0.005));
  border: 1px solid var(--portal-border-subtle);
  border-top: none;
  border-radius: 0 0 14px 14px;
}
.ale-desc {
  font-size: var(--portal-text-base);
  color: rgb(255, 255, 255, 0.75);
  padding: 10px 12px;
  margin-bottom: 14px;
  background: rgb(255, 255, 255, 0.03);
  border-left: 3px solid rgb(var(--accent-rgb), 0.55);
  border-radius: 0 8px 8px 0;
}
.ale-cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 18px;
}
@media (min-width: 900px) {
  .ale-cols {
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  }
}

.ale-col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.ale-col-head h4 {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-black);
  color: rgb(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
  margin: 0;
}
.ale-count {
  font-size: var(--portal-text-2xs);
  color: rgb(255, 255, 255, 0.5);
  font-weight: var(--portal-font-bold);
}
.ale-empty {
  color: rgb(255, 255, 255, 0.3);
  font-size: var(--portal-text-xs);
  padding: 12px 0;
  text-align: center;
}
.ale-loading {
  display: flex;
  justify-content: center;
  padding: 18px;
}

.ale-items {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 320px;
  overflow-y: auto;
}
.ale-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-top: 1px solid var(--portal-border-faint);
  font-size: var(--portal-text-xs);
}
.ale-item:first-child {
  border-top: none;
}
.ale-item-link {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  text-decoration: none;
  color: inherit;
}
.ale-item-link:hover .ale-item-title {
  color: var(--accent-300);
}
.ale-item-poster {
  flex-shrink: 0;
  width: 40px;
  height: 60px;
  border-radius: var(--portal-radius-xs);
  overflow: hidden;
  background: var(--portal-surface-2);
  display: grid;
  place-items: center;
}
.ale-item-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.ale-item-poster-fallback {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-extrabold);
  color: rgb(255, 255, 255, 0.3);
}
.ale-item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.ale-item-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.ale-item-title {
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-medium);
  color: var(--portal-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--portal-dur-fast);
  min-width: 0;
}
.ale-item-copy {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  min-width: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--portal-radius-pill);
  background: var(--portal-surface-3);
  border: 1px solid var(--portal-border-default);
  color: rgb(255, 255, 255, 0.65);
  cursor: pointer;
  opacity: 0;
  transform: translateX(-4px);
  transition:
    opacity 0.18s ease,
    transform 0.18s ease,
    background 0.18s ease,
    color 0.18s ease,
    border-color 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .ale-item:hover .ale-item-copy {
    opacity: 1;
    transform: translateX(0);
  }
  .ale-item-copy:hover {
    background: rgb(var(--accent-rgb), 0.2);
    border-color: var(--accent-500);
    color: #fff;
  }
}
@media (hover: none) {
  .ale-item-copy {
    opacity: 1;
    transform: none;
  }
}
.ale-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ale-item-type {
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 7px;
  border-radius: var(--portal-radius-xs);
  background: rgb(var(--accent-rgb), 0.16);
  color: var(--accent-300);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
}
.ale-item-year {
  font-size: var(--portal-text-2xs);
  color: var(--portal-text-secondary);
  font-weight: var(--portal-font-medium);
}
.ale-item-id {
  font-size: var(--portal-text-2xs);
  color: rgb(255, 255, 255, 0.35);
  font-weight: var(--portal-font-regular);
}
.ale-item-date {
  color: var(--portal-text-muted);
  font-size: var(--portal-text-2xs);
  margin-left: auto;
  flex-shrink: 0;
}
.ale-item-remove {
  width: 28px;
  height: 28px;
  min-width: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--portal-radius-pill);
  border: 1px solid rgb(248, 113, 113, 0.3);
  background: transparent;
  color: var(--portal-color-error-soft);
  cursor: pointer;
  transition: all var(--portal-dur-fast);
  -webkit-tap-highlight-color: transparent;
}
.ale-item-remove:hover {
  background: rgb(248, 113, 113, 0.14);
  border-color: rgb(248, 113, 113, 0.6);
}

.ale-side-block {
  margin-bottom: 16px;
}
.ale-contributors {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ale-contrib {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgb(255, 255, 255, 0.03);
  font-size: var(--portal-text-sm);
}
.ale-contrib-avatar {
  width: 26px;
  height: 26px;
  border-radius: var(--portal-radius-circle);
  background: var(--portal-gradient-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-extrabold);
  color: #fff;
}
.ale-contrib-name {
  flex: 1;
  color: var(--portal-text-body);
  font-weight: var(--portal-font-medium);
  min-width: 0;
}
.ale-contrib-muted {
  font-size: var(--portal-text-sm);
}
.ale-contrib-owner {
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 6px;
  border-radius: var(--portal-radius-xs);
  background: rgb(var(--accent-rgb), 0.18);
  color: var(--accent-300);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  flex-shrink: 0;
}
.ale-contrib-remove {
  background: transparent;
  border: none;
  color: rgb(255, 255, 255, 0.35);
  cursor: pointer;
  font-size: var(--portal-text-base);
  padding: 0 6px;
}
.ale-contrib-remove:hover {
  color: var(--portal-color-error-soft);
}
.ale-add-hint {
  font-size: var(--portal-text-3xs);
  color: rgb(255, 255, 255, 0.3);
}

.ale-history {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ale-event {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  font-size: var(--portal-text-2xs);
}
.ale-event-action {
  font-weight: var(--portal-font-extrabold);
  font-size: var(--portal-text-4xs);
  padding: 2px 7px;
  border-radius: var(--portal-radius-xs);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  background: var(--portal-surface-3);
  color: var(--portal-text-body-muted);
}
.ale-event--added {
  background: rgb(74, 222, 128, 0.14);
  color: var(--portal-color-success-soft);
}
.ale-event--removed {
  background: rgb(248, 113, 113, 0.14);
  color: var(--portal-color-error-soft);
}
.ale-event--copied {
  background: rgb(34, 211, 238, 0.14);
  color: #67e8f9;
}
.ale-event--created {
  background: rgb(var(--portal-color-premium-rgb), 0.14);
  color: var(--portal-color-premium-soft);
}
.ale-event--deleted {
  background: rgb(var(--portal-color-error-rgb), 0.16);
  color: var(--portal-color-error-soft);
}
.ale-event-who {
  color: var(--portal-text-body-muted);
  font-weight: var(--portal-font-bold);
}
.ale-event-date {
  color: rgb(255, 255, 255, 0.35);
  margin-left: auto;
  font-size: var(--portal-text-2xs);
}

.ale-history-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  margin-bottom: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  font: inherit;
  text-align: left;
  -webkit-tap-highlight-color: transparent;
}
.ale-history-toggle-label {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-black);
  color: rgb(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
}
.ale-history-toggle-count {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-bold);
  color: rgb(255, 255, 255, 0.45);
  padding: 1px 7px;
  border-radius: var(--portal-radius-pill);
  background: var(--portal-surface-3);
}
.ale-history-toggle-chev {
  color: rgb(255, 255, 255, 0.45);
  margin-left: auto;
  transition: transform 180ms ease;
}
.ale-history-toggle-chev--open {
  transform: rotate(180deg);
}
@media (hover: hover) {
  .ale-history-toggle:hover .ale-history-toggle-label,
  .ale-history-toggle:hover .ale-history-toggle-chev {
    color: rgb(255, 255, 255, 0.8);
  }
}
</style>
