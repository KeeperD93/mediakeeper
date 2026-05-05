<template>
  <form class="ru-tab ru-form" @submit.prevent="save">
    <div class="ru-form-row">
      <label>
        <span>{{ $t('requestsAdmin.users.drawer.identity.username') }}</span>
        <input type="text" :value="user.username" disabled />
      </label>
    </div>

    <div class="ru-form-row">
      <label>
        <span>{{ $t('requestsAdmin.users.drawer.identity.displayName') }}</span>
        <input v-model="form.display_name" type="text" maxlength="50" />
      </label>
    </div>

    <div class="ru-form-grid">
      <label>
        <span>{{ $t('requestsAdmin.users.drawer.identity.firstName') }}</span>
        <input v-model="form.first_name" type="text" maxlength="100" />
      </label>
      <label>
        <span>{{ $t('requestsAdmin.users.drawer.identity.lastName') }}</span>
        <input v-model="form.last_name" type="text" maxlength="100" />
      </label>
    </div>

    <div class="ru-form-row">
      <label>
        <span>{{ $t('requestsAdmin.users.drawer.identity.email') }}</span>
        <input v-model="form.email" type="email" maxlength="255" />
      </label>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.identity.emailHelp') }}</p>
    </div>

    <div class="ru-tab-section ru-tab-section--meta">
      <dl class="ru-kv">
        <div>
          <dt>{{ $t('requestsAdmin.users.drawer.identity.source') }}</dt>
          <dd>
            {{ user.source === 'emby' ? 'Emby' : $t('requestsAdmin.users.filters.source.local') }}
          </dd>
        </div>
        <div v-if="user.emby_user_id">
          <dt>{{ $t('requestsAdmin.users.drawer.identity.embyId') }}</dt>
          <dd class="ru-mono">{{ user.emby_user_id }}</dd>
        </div>
        <div>
          <dt>{{ $t('requestsAdmin.users.drawer.identity.created') }}</dt>
          <dd>{{ fmt(user.created_at) }}</dd>
        </div>
        <div v-if="user.display_name_changed_at">
          <dt>{{ $t('requestsAdmin.users.drawer.identity.renamedAt') }}</dt>
          <dd>{{ fmt(user.display_name_changed_at) }}</dd>
        </div>
      </dl>
    </div>

    <div class="ru-form-actions">
      <button type="submit" class="ru-btn ru-btn--primary" :disabled="saving">
        {{ saving ? $t('common.saving') : $t('common.save') }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['changed'])

const { t } = useI18n()
const { showToast } = useToast()
const api = usePortalAdminUsers()

const form = reactive({
  display_name: props.user.display_name || '',
  first_name: props.user.first_name || '',
  last_name: props.user.last_name || '',
  email: props.user.email || '',
})
const saving = ref(false)

watch(
  () => props.user,
  u => {
    form.display_name = u.display_name || ''
    form.first_name = u.first_name || ''
    form.last_name = u.last_name || ''
    form.email = u.email || ''
  },
)

async function save() {
  saving.value = true
  try {
    const res = await api.patchIdentity(props.user.id, {
      display_name: form.display_name?.trim() || null,
      first_name: form.first_name?.trim() || null,
      last_name: form.last_name?.trim() || null,
      email: form.email?.trim() || null,
    })
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    saving.value = false
  }
}

function fmt(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}
</script>
