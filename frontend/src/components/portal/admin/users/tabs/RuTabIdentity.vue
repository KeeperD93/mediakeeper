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

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.identity.displayNameResetTitle') }}</h3>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.identity.displayNameResetHelp') }}</p>
      <div class="ru-form-actions ru-form-actions--inline">
        <button
          type="button"
          class="ru-btn ru-btn--ghost"
          :disabled="resetting || user.display_name_must_set"
          @click="onResetDisplayName"
        >
          <RotateCcw :size="16" />
          {{ $t('requestsAdmin.users.drawer.identity.displayNameResetAction') }}
        </button>
        <span v-if="user.display_name_must_set" class="ru-help">
          {{ $t('requestsAdmin.users.drawer.identity.displayNameResetPending') }}
        </span>
      </div>
    </section>

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
import { RotateCcw } from 'lucide-vue-next'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import { localizedDateTime } from '@/utils/datetime'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['changed'])

const { t } = useI18n()
const { showToast } = useToast()
const confirm = useConfirm()
const api = usePortalAdminUsers()

const form = reactive({
  display_name: '',
  first_name: '',
  last_name: '',
  email: '',
})
const saving = ref(false)
const resetting = ref(false)

function hydrate(source) {
  if (!source) return
  form.display_name = source.display_name || ''
  form.first_name = source.first_name || ''
  form.last_name = source.last_name || ''
  form.email = source.email || ''
}

hydrate(props.user)

watch(() => props.user, hydrate, { immediate: true })

async function onResetDisplayName() {
  const ok = await confirm({
    title: t('requestsAdmin.users.drawer.identity.displayNameResetConfirmTitle'),
    message: t('requestsAdmin.users.drawer.identity.displayNameResetConfirm', {
      name: props.user.display_name,
    }),
    confirmLabel: t('requestsAdmin.users.drawer.identity.displayNameResetAction'),
  })
  if (!ok) return
  resetting.value = true
  try {
    const res = await api.resetDisplayName(props.user.id)
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    showToast(t('requestsAdmin.users.toasts.displayNameResetDone'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    resetting.value = false
  }
}

async function save() {
  saving.value = true
  try {
    // Send empty string (not null) when the user has cleared a field so
    // the backend can distinguish a clear from "no change". display_name
    // keeps its anti-empty guard server-side.
    const res = await api.patchIdentity(props.user.id, {
      display_name: form.display_name?.trim() || null,
      first_name: form.first_name ?? '',
      last_name: form.last_name ?? '',
      email: form.email ?? '',
    })
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    if (res?.user) hydrate(res.user)
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } catch (e) {
    const detail = e instanceof Error ? e.message : ''
    showToast(t(`requestsAdmin.users.errors.${detail}`, t('common.error')), TOAST_TYPE.ERR)
  } finally {
    saving.value = false
  }
}

function fmt(value) {
  if (!value) return '—'
  try {
    return localizedDateTime(new Date(value))
  } catch {
    return value
  }
}
</script>
