<template>
  <div class="ru-tab ru-tab-notes">
    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.notes.notesTitle') }}</h3>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.notes.notesHelp') }}</p>
      <textarea
        v-model="notes"
        class="ru-textarea"
        rows="6"
        maxlength="4000"
        :placeholder="$t('requestsAdmin.users.drawer.notes.notesPlaceholder')"
      />
      <div class="ru-form-actions">
        <button type="button" class="ru-btn ru-btn--primary" :disabled="busy" @click="saveNotes">
          {{ $t('common.save') }}
        </button>
      </div>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.notes.tagsTitle') }}</h3>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.notes.tagsHelp') }}</p>

      <div class="ru-tag-row">
        <span v-for="tag in tags" :key="tag" class="ru-tag">
          {{ tag }}
          <button
            type="button"
            class="ru-tag-remove"
            :aria-label="$t('common.delete')"
            @click="removeTag(tag)"
          >
            ×
          </button>
        </span>
        <span v-if="!tags.length" class="ru-help">
          {{ $t('requestsAdmin.users.drawer.notes.noTags') }}
        </span>
      </div>

      <div class="ru-form-actions ru-form-actions--inline">
        <input
          v-model="newTag"
          type="text"
          class="ru-input"
          maxlength="32"
          :placeholder="$t('requestsAdmin.users.drawer.notes.tagPlaceholder')"
          @keydown.enter.prevent="addTag"
        />
        <button
          type="button"
          class="ru-btn ru-btn--ghost"
          :disabled="busy || !newTag"
          @click="addTag"
        >
          + {{ $t('requestsAdmin.users.drawer.notes.addTag') }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['changed'])

const { t } = useI18n()
const { showToast } = useToast()
const api = usePortalAdminUsers()

const busy = ref(false)
const notes = ref(props.user.admin_notes || '')
const tags = ref([...(props.user.tags || [])])
const newTag = ref('')

watch(
  () => props.user,
  u => {
    notes.value = u.admin_notes || ''
    tags.value = [...(u.tags || [])]
  },
)

async function saveNotes() {
  busy.value = true
  try {
    await api.patchNotes(props.user.id, notes.value)
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function syncTags() {
  busy.value = true
  try {
    const res = await api.patchTags(props.user.id, tags.value)
    if (res?.tags) tags.value = res.tags
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function addTag() {
  const value = (newTag.value || '').trim()
  if (!value || tags.value.includes(value)) {
    newTag.value = ''
    return
  }
  tags.value.push(value)
  newTag.value = ''
  await syncTags()
}

async function removeTag(tag) {
  tags.value = tags.value.filter(t => t !== tag)
  await syncTags()
}
</script>
