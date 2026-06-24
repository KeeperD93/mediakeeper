<template>
  <div class="ru-tab ru-tab-access">
    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.access.role') }}</h3>
      <div class="ru-pill-row">
        <button
          v-for="r in presets?.roles || USER_ROLES"
          :key="r"
          type="button"
          class="ru-pill"
          :class="{ 'ru-pill--active': user.role === r }"
          :disabled="busy"
          @click="changeRole(r)"
        >
          {{ $t(`requestsAdmin.users.filters.role.${r}`) }}
        </button>
      </div>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.access.roleHelp') }}</p>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.access.permissions') }}</h3>
      <ul class="ru-perm-list">
        <li v-for="key in PERMISSION_KEYS" :key="key" class="ru-perm-row">
          <div class="ru-perm-head">
            <label class="ru-switch">
              <input
                type="checkbox"
                :checked="user.permissions?.[key]"
                :disabled="busy"
                @change="togglePerm(key, $event.target.checked)"
              />
              <span />
            </label>
            <span class="ru-perm-label">{{ $t(`requestsAdmin.users.permissions.${key}`) }}</span>
          </div>
          <p class="ru-help">{{ $t(`requestsAdmin.users.permissionsHelp.${key}`) }}</p>
        </li>
      </ul>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.access.window') }}</h3>
      <div class="ru-form-grid">
        <label>
          <span>{{ $t('requestsAdmin.users.drawer.access.startDate') }}</span>
          <input v-model="accessWindow.start" type="datetime-local" />
        </label>
        <label>
          <span>{{ $t('requestsAdmin.users.drawer.access.endDate') }}</span>
          <input v-model="accessWindow.end" type="datetime-local" />
        </label>
      </div>
      <div class="ru-form-actions ru-form-actions--inline">
        <button type="button" class="ru-btn ru-btn--primary" :disabled="busy" @click="saveWindow">
          {{ $t('common.save') }}
        </button>
        <span class="ru-form-divider" />
        <span class="ru-help">{{ $t('requestsAdmin.users.drawer.access.extend') }}</span>
        <button
          v-for="m in EXTEND_PRESETS"
          :key="m"
          type="button"
          class="ru-pill"
          :disabled="busy"
          @click="extend(m)"
        >
          {{ $t('requestsAdmin.users.drawer.access.extendBtn', { n: m }) }}
        </button>
      </div>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.access.activation') }}</h3>
      <div class="ru-toggle-row">
        <label class="ru-switch">
          <input
            type="checkbox"
            :checked="user.account_active"
            :disabled="busy"
            @change="toggleActive($event.target.checked)"
          />
          <span />
        </label>
        <div>
          <strong>{{ $t('requestsAdmin.users.drawer.access.accountActive') }}</strong>
          <p class="ru-help">{{ $t('requestsAdmin.users.drawer.access.accountActiveHelp') }}</p>
        </div>
      </div>

      <div v-if="user.source === USER_SOURCE.EMBY" class="ru-toggle-row">
        <label class="ru-switch">
          <input
            type="checkbox"
            :checked="!user.emby_is_disabled"
            :disabled="busy || !user.emby_user_id"
            @change="toggleEmby($event.target.checked)"
          />
          <span />
        </label>
        <div>
          <strong>{{ $t('requestsAdmin.users.drawer.access.embyEnabled') }}</strong>
          <p class="ru-help">{{ $t('requestsAdmin.users.drawer.access.embyEnabledHelp') }}</p>
          <p v-if="!user.emby_user_id" class="ru-form-error">
            {{ $t('requestsAdmin.users.errors.no_emby_link') }}
          </p>
        </div>
      </div>
    </section>

    <section class="ru-tab-section ru-tab-section--danger">
      <h3>{{ $t('requestsAdmin.users.drawer.access.dangerZone') }}</h3>
      <div v-if="!user.deleted_at">
        <p class="ru-help">{{ $t('requestsAdmin.users.drawer.access.deleteHelp') }}</p>
        <ul class="ru-danger-list">
          <li>{{ $t('requestsAdmin.users.drawer.access.deleteBullet1') }}</li>
          <li>{{ $t('requestsAdmin.users.drawer.access.deleteBullet2') }}</li>
          <li>{{ $t('requestsAdmin.users.drawer.access.deleteBullet3') }}</li>
        </ul>
        <div class="ru-form-actions ru-form-actions--inline">
          <button type="button" class="ru-btn ru-btn--danger" :disabled="busy" @click="onDelete">
            {{ $t('requestsAdmin.users.drawer.access.deleteAction') }}
          </button>
        </div>
      </div>
      <div v-else>
        <p class="ru-help">{{ $t('requestsAdmin.users.drawer.access.restoreHelp') }}</p>
        <div class="ru-form-actions ru-form-actions--inline">
          <button type="button" class="ru-btn ru-btn--ghost" :disabled="busy" @click="onRestore">
            {{ $t('requestsAdmin.users.actions.restore') }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import {
  PERMISSION_KEYS,
  USER_ROLES,
  USER_SOURCE,
  EXTEND_PRESETS,
} from '@/constants/portalAdminUsers'

const props = defineProps({
  user: { type: Object, required: true },
  presets: { type: Object, default: null },
})
const emit = defineEmits(['changed'])

const { t } = useI18n()
const { showToast } = useToast()
const confirm = useConfirm()
const api = usePortalAdminUsers()

const busy = ref(false)
const accessWindow = reactive({
  start: toLocal(props.user.access_start_date || props.user.created_at),
  end: toLocal(props.user.access_end_date),
})

watch(
  () => props.user,
  u => {
    accessWindow.start = toLocal(u.access_start_date || u.created_at)
    accessWindow.end = toLocal(u.access_end_date)
  },
)

function toLocal(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const pad = v => String(v).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return ''
  }
}

function toIso(local) {
  if (!local) return null
  try {
    return new Date(local).toISOString()
  } catch {
    return null
  }
}

async function changeRole(role) {
  busy.value = true
  try {
    await api.patchRole(props.user.id, role)
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function togglePerm(key, value) {
  busy.value = true
  try {
    await api.patchPermissions(props.user.id, { [key]: value })
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function saveWindow() {
  busy.value = true
  try {
    await api.patchAccess(props.user.id, {
      start: toIso(accessWindow.start),
      end: toIso(accessWindow.end),
    })
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function extend(months) {
  busy.value = true
  try {
    await api.postExtendAccess(props.user.id, months)
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function toggleActive(active) {
  if (!active) {
    const ok = await confirm({
      title: t('requestsAdmin.users.confirms.deactivateTitle'),
      message: t('requestsAdmin.users.confirms.deactivate', { name: props.user.display_name }),
      variant: 'danger',
      confirmLabel: t('requestsAdmin.users.actions.deactivate'),
    })
    if (!ok) return
  }
  busy.value = true
  try {
    const res = await api.patchActive(props.user.id, active)
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function toggleEmby(enabled) {
  if (!enabled) {
    const ok = await confirm({
      title: t('requestsAdmin.users.confirms.deactivateEmbyTitle'),
      message: t('requestsAdmin.users.confirms.deactivateEmby', { name: props.user.display_name }),
      variant: 'danger',
      confirmLabel: t('requestsAdmin.users.actions.deactivate'),
    })
    if (!ok) return
  }
  busy.value = true
  try {
    const res = await api.postEmbyToggle(props.user.id, enabled)
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    showToast(
      t(
        enabled
          ? 'requestsAdmin.users.toasts.embyEnabled'
          : 'requestsAdmin.users.toasts.embyDisabled',
      ),
      TOAST_TYPE.OK,
    )
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function onDelete() {
  const ok = await confirm({
    title: t('common.confirmTitle.deleteUser'),
    message: t('requestsAdmin.users.confirms.delete', { name: props.user.display_name }),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  busy.value = true
  try {
    await api.softDelete(props.user.id)
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function onRestore() {
  busy.value = true
  try {
    await api.restoreUser(props.user.id)
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    busy.value = false
  }
}
</script>
