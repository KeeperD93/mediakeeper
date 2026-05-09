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
          <ListItemRow
            v-for="item in detail.items"
            :key="item.id"
            :item="item"
            :copied="copiedId === item.id"
            :can-edit="canEdit"
            :format-date="formatDate"
            @copy="copyTitle"
            @remove="$emit('remove-item', $event)"
          />
        </ul>
      </div>

      <!-- Contributors + history column -->
      <aside v-if="lst.privacy !== 'private'" class="ale-col ale-col--side">
        <ListContributors
          :contributors="allContributors"
          :is-owner="lst.is_owner"
          @remove="$emit('remove-contributor', $event)"
        />
        <ListHistory
          v-model:history-open="historyOpen"
          :history="history"
          :loading-history="loadingHistory"
          :action-label="actionLabel"
          :format-date="formatDate"
        />
      </aside>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalLists } from '@/composables/portal/usePortalLists'
import MkSpinner from '@/components/common/MkSpinner.vue'
import ListItemRow from './ListExpansion/ListItemRow.vue'
import ListContributors from './ListExpansion/ListContributors.vue'
import ListHistory from './ListExpansion/ListHistory.vue'

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
</style>
