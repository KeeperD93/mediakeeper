<template>
  <div class="ru-tab ru-tab-security">
    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.security.lastLogin') }}</h3>
      <dl class="ru-kv">
        <div>
          <dt>{{ $t('requestsAdmin.users.drawer.security.lastLoginAt') }}</dt>
          <dd>{{ fmt(user.last_login_at) || $t('requestsAdmin.users.labels.neverLoggedIn') }}</dd>
        </div>
        <div>
          <dt>{{ $t('requestsAdmin.users.drawer.security.ip') }}</dt>
          <dd class="ru-mono">{{ user.last_login_ip || '—' }}</dd>
        </div>
        <div>
          <dt>{{ $t('requestsAdmin.users.drawer.security.userAgent') }}</dt>
          <dd class="ru-ua">{{ shortUa(user.last_login_user_agent) || '—' }}</dd>
        </div>
        <div>
          <dt>{{ $t('requestsAdmin.users.drawer.security.lastSeen') }}</dt>
          <dd>{{ fmt(user.last_seen_at) || '—' }}</dd>
        </div>
        <div>
          <dt>{{ $t('requestsAdmin.users.drawer.security.firstSeen') }}</dt>
          <dd>{{ fmt(user.created_at) || '—' }}</dd>
        </div>
      </dl>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.security.sessions') }}</h3>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.security.sessionsHelp') }}</p>
      <div class="ru-form-actions ru-form-actions--inline">
        <button type="button" class="ru-btn ru-btn--ghost" :disabled="busy" @click="onForceLogout">
          <LogOut :size="16" />
          {{ $t('requestsAdmin.users.drawer.security.forceLogoutMk') }}
        </button>
        <span v-if="user.tokens_invalidated_at" class="ru-help">
          {{
            $t('requestsAdmin.users.drawer.security.lastForceLogout', {
              at: fmt(user.tokens_invalidated_at),
            })
          }}
        </span>
      </div>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.security.forceLogoutScope') }}</p>
    </section>

    <section v-if="user.source === 'local'" class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.security.passwordReset') }}</h3>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.security.passwordResetHelp') }}</p>
      <button type="button" class="ru-btn ru-btn--ghost" :disabled="busy" @click="onResetPassword">
        <KeyRound :size="16" />
        {{ $t('requestsAdmin.users.drawer.security.passwordResetAction') }}
      </button>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.security.export') }}</h3>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.security.exportHelp') }}</p>
      <div class="ru-form-actions ru-form-actions--inline">
        <button type="button" class="ru-btn ru-btn--ghost" :disabled="busy" @click="exportJson">
          <Download :size="16" />
          {{ $t('requestsAdmin.users.actions.exportJson') }}
        </button>
        <a class="ru-btn ru-btn--ghost" :href="api.exportUserCsvUrl(user.id)" download>
          <FileSpreadsheet :size="16" />
          {{ $t('requestsAdmin.users.actions.exportCsv') }}
        </a>
      </div>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.security.notify') }}</h3>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.security.notifyHelp') }}</p>
      <button type="button" class="ru-btn ru-btn--ghost" @click="notifyOpen = true">
        <Send :size="16" />
        {{ $t('requestsAdmin.users.actions.notify') }}
      </button>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.security.loginHistory') }}</h3>
      <div v-if="loadingHistory" class="ru-loading">{{ $t('common.loading') }}</div>
      <p v-else-if="!history.length" class="ru-help">
        {{ $t('requestsAdmin.users.drawer.security.loginHistoryEmpty') }}
      </p>
      <ol v-else class="ru-feed-list">
        <li v-for="h in history" :key="h.id" class="ru-feed-row">
          <span class="ru-feed-date">{{ fmt(h.created_at) }}</span>
          <span class="ru-feed-main">
            <RuUserBadge :variant="h.success ? 'success' : 'danger'">
              {{
                h.success
                  ? $t('requestsAdmin.users.drawer.security.loginOk')
                  : $t('requestsAdmin.users.drawer.security.loginFail')
              }}
            </RuUserBadge>
            <span v-if="h.ip" class="ru-mono">{{ h.ip }}</span>
          </span>
          <span class="ru-feed-tail" :title="h.user_agent">{{ shortUa(h.user_agent) }}</span>
        </li>
      </ol>
      <PortalLoadMore
        :show="historyHasMore"
        :loading="loadingMoreHistory"
        @load="loadMoreHistory"
      />
    </section>

    <RuNotifyModal :open="notifyOpen" :user="user" @close="notifyOpen = false" @sent="onSent" />
    <RuPasswordResetModal
      :open="!!resetPassword"
      :password="resetPassword || ''"
      @close="resetPassword = null"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, FileSpreadsheet, KeyRound, LogOut, Send } from 'lucide-vue-next'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import { downloadJsonFile } from '@/composables/portal/useFileDownload'
import RuNotifyModal from '../RuNotifyModal.vue'
import RuPasswordResetModal from '../RuPasswordResetModal.vue'
import RuUserBadge from '../RuUserBadge.vue'
import PortalLoadMore from '@/components/portal/PortalLoadMore.vue'
import { localizedDateTime } from '@/utils/datetime'
import '@/assets/styles/portal/admin-users-feed.css'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['changed'])

const { t } = useI18n()
const { showToast } = useToast()
const confirm = useConfirm()
const api = usePortalAdminUsers()

const busy = ref(false)
const notifyOpen = ref(false)
const resetPassword = ref(null)
const LOGIN_PAGE = 100
const history = ref([])
const loadingHistory = ref(false)
const loadingMoreHistory = ref(false)
const historyHasMore = ref(false)

async function loadHistory() {
  if (!props.user?.id) return
  loadingHistory.value = true
  try {
    const res = await api.fetchLoginHistory(props.user.id, { limit: LOGIN_PAGE, offset: 0 })
    history.value = res?.items || []
    historyHasMore.value = history.value.length === LOGIN_PAGE
  } finally {
    loadingHistory.value = false
  }
}

async function loadMoreHistory() {
  if (loadingMoreHistory.value || !historyHasMore.value) return
  loadingMoreHistory.value = true
  try {
    const res = await api.fetchLoginHistory(props.user.id, {
      limit: LOGIN_PAGE,
      offset: history.value.length,
    })
    const items = res?.items || []
    history.value = [...history.value, ...items]
    historyHasMore.value = items.length === LOGIN_PAGE
  } finally {
    loadingMoreHistory.value = false
  }
}
watch(() => props.user.id, loadHistory)
onMounted(loadHistory)

async function exportJson() {
  busy.value = true
  try {
    const data = await api.exportUser(props.user.id)
    downloadJsonFile(data, `mk-user-${props.user.id}.json`)
    showToast(t('requestsAdmin.users.toasts.exported'), TOAST_TYPE.OK)
  } finally {
    busy.value = false
  }
}

async function onForceLogout() {
  const ok = await confirm({
    title: t('requestsAdmin.users.drawer.security.forceLogoutConfirmTitle'),
    message: t('requestsAdmin.users.drawer.security.forceLogoutConfirm', {
      name: props.user.display_name,
    }),
    variant: 'danger',
    confirmLabel: t('requestsAdmin.users.drawer.security.forceLogoutMk'),
  })
  if (!ok) return
  busy.value = true
  try {
    const res = await api.forceLogout(props.user.id)
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    showToast(t('requestsAdmin.users.toasts.forceLogoutDone'), TOAST_TYPE.OK)
    emit('changed')
    await loadHistory()
  } finally {
    busy.value = false
  }
}

async function onResetPassword() {
  const ok = await confirm({
    title: t('requestsAdmin.users.drawer.security.passwordResetConfirmTitle'),
    message: t('requestsAdmin.users.drawer.security.passwordResetConfirm', {
      name: props.user.display_name,
    }),
    variant: 'danger',
    confirmLabel: t('requestsAdmin.users.drawer.security.passwordResetAction'),
  })
  if (!ok) return
  busy.value = true
  try {
    const res = await api.resetPassword(props.user.id)
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    resetPassword.value = res.password
    emit('changed')
  } finally {
    busy.value = false
  }
}

function fmt(value) {
  if (!value) return ''
  try {
    return localizedDateTime(new Date(value))
  } catch {
    return value
  }
}

function shortUa(ua) {
  if (!ua) return ''
  return ua.length > 80 ? `${ua.slice(0, 77)}…` : ua
}

function onSent() {
  notifyOpen.value = false
  showToast(t('requestsAdmin.users.toasts.notified'), TOAST_TYPE.OK)
}
</script>
