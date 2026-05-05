<template>
  <Teleport to="body">
    <transition name="atl-fade">
      <div
        v-if="open"
        class="atl-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('portal.lists.addTo.title')"
        @click.self="close"
        @keydown.esc="close"
      >
        <div class="atl-panel mk-modal-sheet-panel" tabindex="-1">
          <div class="atl-header">
            <h2 class="atl-title">{{ $t('portal.lists.addTo.title') }}</h2>
            <button class="atl-close" type="button" :aria-label="$t('common.close')" @click="close">
              <X :size="14" />
            </button>
          </div>

          <div v-if="media" class="atl-media">
            <span class="atl-media-type">{{ media.media_type }}</span>
            <span class="atl-media-title">{{ media.title }}</span>
          </div>

          <div class="atl-body">
            <div class="atl-tabs" role="tablist">
              <button
                v-for="tabDef in TABS"
                :key="tabDef.id"
                type="button"
                role="tab"
                :aria-selected="tab === tabDef.id"
                class="atl-tab"
                :class="{ 'atl-tab--active': tab === tabDef.id }"
                @click="tab = tabDef.id"
              >
                {{ $t(tabDef.label) }}
                <span class="atl-tab-count">{{ listsByTab[tabDef.id].length }}</span>
              </button>
            </div>

            <p v-if="!listsByTab[tab].length" class="atl-empty">
              {{ $t('portal.lists.emptyOwn') }}
            </p>

            <ul v-else class="atl-list">
              <li v-for="lst in listsByTab[tab]" :key="lst.id">
                <button
                  type="button"
                  class="atl-row"
                  :disabled="busy || inList(lst.id) || !lst.is_editable"
                  :title="!lst.is_editable ? $t('portal.lists.addTo.readOnlyHint') : ''"
                  @click="pickList(lst)"
                >
                  <span class="atl-row-name">{{ lst.name }}</span>
                  <span v-if="!lst.is_editable" class="atl-row-readonly">
                    {{ $t('portal.lists.addTo.readOnly') }}
                  </span>
                  <span class="atl-row-priv" :class="`atl-row-priv--${lst.privacy}`">
                    {{ $t(`portal.lists.privacy.${lst.privacy}`) }}
                  </span>
                  <span class="atl-row-count">{{ lst.item_count }}</span>
                </button>
              </li>
            </ul>

            <button
              type="button"
              class="atl-row atl-row--create"
              :disabled="busy"
              @click="showCreate = true"
            >
              + {{ $t('portal.lists.addTo.createNew') }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <ListFormModal
      :open="showCreate"
      mode="create"
      @close="showCreate = false"
      @submit="onCreate"
    />
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'
import { usePortalLists } from '@/composables/portal/usePortalLists'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import ListFormModal from './ListFormModal.vue'
import { MEDIA_TYPE } from '@/constants/media'

const props = defineProps({
  open: { type: Boolean, default: false },
  media: { type: Object, default: null },
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const { showToast } = useToast()
const svc = usePortalLists()

const lists = svc.lists
const publicLists = svc.publicLists
const busy = ref(false)
const showCreate = ref(false)
const picked = ref([])
const tab = ref('private')

const TABS = [
  { id: 'private', label: 'portal.lists.privacy.private' },
  { id: 'public', label: 'portal.lists.addTo.tabPublic' },
]

// Union of fetchMyLists (owner + collab-contributor) and fetchPublicLists
// (everything public/collaborative, everyone). A list is editable if the
// user owns it or its privacy is collaborative — collaborative means
// anyone can add; the backend auto-enrols the user as contributor on
// first add. Only public_readonly lists not owned are read-only here.
const isEditable = l => l.is_owner || l.privacy === 'collaborative'
const allLists = computed(() => {
  const byId = new Map()
  for (const l of lists.value) byId.set(l.id, { ...l, is_editable: isEditable(l) })
  for (const l of publicLists.value) {
    if (!byId.has(l.id)) byId.set(l.id, { ...l, is_editable: isEditable(l) })
  }
  return Array.from(byId.values())
})

const listsByTab = computed(() => ({
  private: allLists.value.filter(l => l.is_owner && l.privacy === 'private'),
  public: allLists.value.filter(l => l.privacy !== 'private'),
}))

function inList(id) {
  return picked.value.includes(id)
}

watch(
  () => props.open,
  async v => {
    if (v) await Promise.all([svc.fetchMyLists(), svc.fetchPublicLists()])
    else picked.value = []
  },
  { immediate: false },
)

function close() {
  if (!busy.value) emit('close')
}

async function addMediaToList(listId) {
  if (!props.media) return null
  const m = props.media
  const payload = [
    {
      tmdb_id: m.tmdb_id || m.id,
      media_type: m.media_type || MEDIA_TYPE.MOVIE,
      title: m.title,
      poster_url: m.poster_url || m.poster || null,
      year: m.year || (m.release_date ? Number(String(m.release_date).slice(0, 4)) : null),
    },
  ]
  return await svc.addItems(listId, payload)
}

async function pickList(lst) {
  if (busy.value) return
  busy.value = true
  try {
    const res = await addMediaToList(lst.id)
    if (res?.success) {
      picked.value = [...picked.value, lst.id]
      if (res.duplicates) {
        showToast(t('portal.lists.addTo.duplicate'), TOAST_TYPE.WARN)
      } else {
        showToast(t('portal.lists.addTo.added', { name: lst.name }), TOAST_TYPE.OK)
      }
      await svc.fetchMyLists()
    }
  } finally {
    busy.value = false
  }
}

async function onCreate(data) {
  busy.value = true
  try {
    const created = await svc.createList(data)
    if (created?.success) {
      showCreate.value = false
      await svc.fetchMyLists()
      await addMediaToList(created.id)
      showToast(t('portal.lists.addTo.added', { name: data.name }), TOAST_TYPE.OK)
    }
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.atl-overlay {
  z-index: 9998;
}
.atl-panel {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 0.5px solid var(--portal-border-default);
  outline: none;
}
@media (min-width: 768px) {
  .atl-panel {
    max-width: 440px;
    max-height: 78vh;
  }
}

.atl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 10px;
}
.atl-title {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  margin: 0;
}
.atl-close {
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  border: none;
  border-radius: var(--radius-btn);
  background: var(--portal-surface-2);
  color: var(--text-muted);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .atl-close:hover {
    background: var(--portal-surface-4);
    color: var(--text-primary);
  }
}

.atl-media {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 18px;
  font-size: var(--portal-text-xs);
  color: var(--text-secondary);
  border-bottom: 0.5px solid rgb(255, 255, 255, 0.05);
}
.atl-media-type {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-300);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
}
.atl-media-title {
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
}

.atl-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 10px 16px;
}
.atl-tabs {
  display: flex;
  gap: 6px;
  padding: 4px 2px 10px;
  border-bottom: 1px solid rgb(255, 255, 255, 0.05);
  margin-bottom: 10px;
}
.atl-tab {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 12px;
  border-radius: var(--radius-btn);
  border: 1px solid transparent;
  background: transparent;
  color: rgb(255, 255, 255, 0.65);
  font: inherit;
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-bold);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    background 160ms ease,
    color 160ms ease,
    border-color 160ms ease;
}
@media (hover: hover) {
  .atl-tab:hover {
    background: var(--portal-surface-2);
    color: var(--text-primary);
  }
}
.atl-tab--active {
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-300);
  border-color: rgb(var(--accent-rgb), 0.4);
}
.atl-tab-count {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  padding: 1px 6px;
  border-radius: var(--portal-radius-pill);
  background: var(--portal-surface-3);
  color: var(--portal-text-secondary);
}
.atl-tab--active .atl-tab-count {
  background: rgb(var(--accent-rgb), 0.22);
  color: var(--accent-300);
}
.atl-row-readonly {
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 6px;
  border-radius: var(--portal-radius-xs);
  background: rgb(156, 163, 175, 0.18);
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  flex-shrink: 0;
}
.atl-empty {
  color: var(--text-muted);
  font-size: var(--portal-text-sm);
  text-align: center;
  padding: 1rem;
}
.atl-picker-label {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  padding: 4px 10px 6px;
}

.atl-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.atl-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  min-height: 44px;
  background: transparent;
  color: inherit;
  border: 1px solid transparent;
  border-radius: var(--radius-btn);
  font-size: var(--portal-text-sm);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .atl-row:hover:not(:disabled) {
    background: var(--portal-surface-2);
    border-color: var(--portal-border-subtle);
  }
}
.atl-row:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.atl-row--create {
  margin-top: 8px;
  border: 1px dashed rgb(var(--accent-rgb), 0.35);
  color: var(--accent-300);
  font-weight: var(--portal-font-bold);
  justify-content: center;
}
.atl-row-name {
  flex: 1;
  font-weight: var(--portal-font-medium);
}
.atl-row-priv {
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  flex-shrink: 0;
}
.atl-row-priv--private {
  background: rgb(156, 163, 175, 0.18);
  color: #d1d5db;
}
.atl-row-priv--public_readonly {
  background: rgb(var(--portal-color-info-rgb), 0.18);
  color: var(--portal-color-info-soft);
}
.atl-row-priv--collaborative {
  background: rgb(var(--portal-color-premium-rgb), 0.18);
  color: var(--portal-color-premium-soft);
}
.atl-row-count {
  font-size: var(--portal-text-2xs);
  color: var(--text-muted);
  font-weight: var(--portal-font-bold);
  flex-shrink: 0;
}

.atl-fade-enter-active {
  transition: all var(--portal-dur-base) ease;
}
.atl-fade-leave-active {
  transition: all var(--portal-dur-fast) ease;
}
.atl-fade-enter-from,
.atl-fade-leave-to {
  opacity: 0;
}
.atl-fade-enter-from .atl-panel {
  transform: translateY(12px) scale(0.97);
}
.atl-fade-leave-to .atl-panel {
  transform: translateY(6px) scale(0.98);
}
</style>
