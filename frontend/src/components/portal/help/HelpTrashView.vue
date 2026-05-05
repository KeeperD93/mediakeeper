<template>
  <div class="pt-help-trash">
    <header class="pt-help-trash-head">
      <button
        type="button"
        class="pt-help-edit-action pt-help-edit-action--ghost"
        @click="$emit('back')"
      >
        <ArrowLeft :size="14" />
        {{ $t('portal.help.backToList') }}
      </button>
      <h3 class="pt-help-trash-title">
        <Trash2 :size="18" />
        {{ $t('portal.help.admin.trashTitle') }}
      </h3>
      <span class="pt-help-trash-retention">
        {{ $t('portal.help.admin.retention', { days: retentionDays }) }}
      </span>
    </header>

    <div v-if="loading" class="pt-help-state">
      <MkSpinner size="sm" inline />
      {{ $t('common.loading') }}
    </div>

    <div v-else-if="!items.length" class="pt-help-state pt-help-state--empty">
      {{ $t('portal.help.admin.trashEmpty') }}
    </div>

    <ul v-else class="pt-help-trash-list">
      <li v-for="a in items" :key="a.id" class="pt-help-trash-row">
        <div class="pt-help-trash-row-body">
          <h4 class="pt-help-trash-row-title">{{ a.title || $t('portal.help.admin.untitled') }}</h4>
          <p class="pt-help-trash-row-meta">
            {{ $t('portal.help.categories.' + a.category) }}
            ·
            {{ $t('portal.help.admin.deletedOn', { date: formatDate(a.deleted_at) }) }}
            ·
            {{ remainingLabel(a.deleted_at) }}
          </p>
        </div>
        <div class="pt-help-trash-row-actions">
          <button type="button" class="pt-help-edit-action" @click="onRestore(a.id)">
            <RotateCcw :size="14" />
            {{ $t('portal.help.admin.restore') }}
          </button>
          <button
            type="button"
            class="pt-help-edit-action pt-help-edit-action--danger"
            @click="onHardDelete(a.id)"
          >
            <Trash2 :size="14" />
            {{ $t('portal.help.admin.deleteForever') }}
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, RotateCcw, Trash2 } from 'lucide-vue-next'

import MkSpinner from '@/components/common/MkSpinner.vue'
import { usePortalHelpAdmin } from '@/composables/portal/usePortalHelpAdmin'

const props = defineProps({
  lang: { type: String, default: 'fr' },
})
const emit = defineEmits(['back', 'restored', 'purged'])

const { t } = useI18n()
const { listTrash, restore, hardDelete } = usePortalHelpAdmin()

const items = ref([])
const retentionDays = ref(30)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await listTrash({ lang: props.lang })
    items.value = res.items
    retentionDays.value = res.retentionDays
  } finally {
    loading.value = false
  }
}

async function onRestore(id) {
  await restore(id)
  items.value = items.value.filter(a => a.id !== id)
  emit('restored', id)
}

async function onHardDelete(id) {
  // eslint-disable-next-line no-alert
  if (!window.confirm(t('portal.help.admin.confirmHardDelete'))) return
  await hardDelete(id)
  items.value = items.value.filter(a => a.id !== id)
  emit('purged', id)
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString()
  } catch {
    return iso
  }
}

function remainingLabel(iso) {
  if (!iso) return ''
  const deletedAt = new Date(iso).getTime()
  const expiresAt = deletedAt + retentionDays.value * 24 * 60 * 60 * 1000
  const days = Math.max(0, Math.round((expiresAt - Date.now()) / (24 * 60 * 60 * 1000)))
  return t('portal.help.admin.daysLeft', { days })
}

onMounted(load)
defineExpose({ reload: load })
</script>

<!-- Styles externalised to assets/styles/portal/help-overlay-admin.css -->
