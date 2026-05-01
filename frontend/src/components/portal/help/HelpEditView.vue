<template>
  <div class="pt-help-edit">
    <!-- Top bar: title field + meta selectors + save state + delete -->
    <header class="pt-help-edit-head">
      <input
        v-model="local.title"
        class="pt-help-edit-title"
        :placeholder="$t('portal.help.admin.titlePlaceholder')"
        @input="scheduleSave"
      />
      <span class="pt-help-edit-status" :class="statusClass">
        <component :is="statusIcon" :size="13" />
        {{ statusLabel }}
      </span>
    </header>

    <div class="pt-help-edit-meta">
      <label class="pt-help-edit-field">
        <span>{{ $t('portal.help.admin.fieldCategory') }}</span>
        <select v-model="local.category" class="pt-help-edit-select" @change="scheduleSave">
          <option v-for="cat in CATEGORIES" :key="cat" :value="cat">
            {{ $t('portal.help.categories.' + cat) }}
          </option>
        </select>
      </label>
      <label class="pt-help-edit-field">
        <span>{{ $t('portal.help.admin.fieldIcon') }}</span>
        <select v-model="local.icon" class="pt-help-edit-select" @change="scheduleSave">
          <option value="">—</option>
          <option v-for="ic in HELP_ICON_NAMES" :key="ic" :value="ic">{{ ic }}</option>
        </select>
      </label>
      <label class="pt-help-edit-field">
        <span>{{ $t('portal.help.admin.fieldOrder') }}</span>
        <input
          v-model.number="local.sortOrder"
          type="number"
          class="pt-help-edit-input"
          min="0"
          @change="scheduleSave"
        />
      </label>
      <label class="pt-help-edit-field pt-help-edit-toggle">
        <input
          type="checkbox"
          :checked="!local.isDraft"
          @change="setPublished($event.target.checked)"
        />
        <span>{{ $t('portal.help.admin.published') }}</span>
      </label>
    </div>

    <HelpEditor v-model="local.bodyHtml" @update:modelValue="scheduleSave" />

    <footer class="pt-help-edit-foot">
      <button
        type="button"
        class="pt-help-edit-action pt-help-edit-action--ghost"
        @click="$emit('back')"
      >
        <ArrowLeft :size="14" />
        {{ $t('portal.help.backToList') }}
      </button>
      <button
        type="button"
        class="pt-help-edit-action pt-help-edit-action--danger"
        @click="onDelete"
      >
        <Trash2 :size="14" />
        {{ $t('common.delete') }}
      </button>
    </footer>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, Check, Loader2, Trash2 } from 'lucide-vue-next'

import HelpEditor from './HelpEditor.vue'
import { usePortalHelpAdmin } from '@/composables/portal/usePortalHelpAdmin'
import { HELP_ICON_NAMES } from '@/utils/portal/helpIconMap'

const CATEGORIES = ['general', 'requests', 'profile', 'lists', 'issues', 'misc']
const SAVE_DEBOUNCE_MS = 1500

const props = defineProps({
  article: { type: Object, required: true },
  lang: { type: String, default: 'fr' },
})
const emit = defineEmits(['back', 'updated', 'deleted'])

const { t } = useI18n()
const { patchMetadata, putTranslation, softDelete } = usePortalHelpAdmin()

const local = reactive({
  title: props.article.title || '',
  bodyHtml: props.article.body_html || '',
  category: props.article.category || 'general',
  icon: props.article.icon || '',
  sortOrder: props.article.sort_order || 0,
  isDraft: !!props.article.is_draft,
})

const saveState = ref('idle') // idle | dirty | saving | saved | error
let saveTimer = null
let pendingMeta = false
let pendingTranslation = false
let inFlight = false

function scheduleSave() {
  saveState.value = 'dirty'
  pendingTranslation = true
  pendingMeta = true
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(commit, SAVE_DEBOUNCE_MS)
}

async function commit() {
  if (inFlight) return // a previous commit will pick up the latest state on its next tick
  inFlight = true
  saveState.value = 'saving'
  try {
    // Snapshot the pending flags BEFORE the awaits so concurrent edits
    // (which re-set them to true) don't get silently dropped when we
    // reset them below.
    const wantMeta = pendingMeta
    const wantTranslation = pendingTranslation
    pendingMeta = false
    pendingTranslation = false

    if (wantMeta) {
      await patchMetadata(props.article.id, {
        category: local.category,
        icon: local.icon || null,
        sort_order: local.sortOrder,
        is_draft: local.isDraft,
      })
    }
    if (wantTranslation) {
      await putTranslation(props.article.id, props.lang, {
        title: local.title.trim() || t('portal.help.admin.untitled'),
        bodyHtml: local.bodyHtml,
      })
    }
    saveState.value = pendingMeta || pendingTranslation ? 'dirty' : 'saved'
    emit('updated')
  } catch {
    saveState.value = 'error'
    // Restore the flags so the next debounce retries the failed payload.
    pendingMeta = true
    pendingTranslation = true
  } finally {
    inFlight = false
    // If new edits landed during the flight, re-arm the debounce.
    if (pendingMeta || pendingTranslation) {
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(commit, SAVE_DEBOUNCE_MS)
    }
  }
}

function setPublished(published) {
  local.isDraft = !published
  scheduleSave()
}

async function onDelete() {
  // eslint-disable-next-line no-alert
  if (!window.confirm(t('portal.help.admin.confirmDelete'))) return
  try {
    await softDelete(props.article.id)
    emit('deleted', props.article.id)
  } catch {
    saveState.value = 'error'
  }
}

const statusLabel = computed(() => {
  switch (saveState.value) {
    case 'saving': return t('portal.help.admin.saving')
    case 'saved':  return t('portal.help.admin.saved')
    case 'dirty':  return t('portal.help.admin.unsaved')
    case 'error':  return t('portal.help.admin.errorSave')
    default:       return ''
  }
})
const statusIcon = computed(() =>
  saveState.value === 'saving' ? Loader2 : Check,
)
const statusClass = computed(() => `pt-help-edit-status--${saveState.value}`)

watch(
  () => props.article?.id,
  () => {
    Object.assign(local, {
      title: props.article.title || '',
      bodyHtml: props.article.body_html || '',
      category: props.article.category || 'general',
      icon: props.article.icon || '',
      sortOrder: props.article.sort_order || 0,
      isDraft: !!props.article.is_draft,
    })
    saveState.value = 'idle'
  },
)
</script>

<!-- Styles externalised to assets/styles/portal/help-overlay-admin.css -->
