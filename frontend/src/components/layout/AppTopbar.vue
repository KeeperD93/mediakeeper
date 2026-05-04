<template>
  <header class="mk-topbar">
    <!-- Left: burger + breadcrumb -->
    <div class="tb-left">
      <button class="tb-burger" @click="emit('toggleMobile')">
        <Menu :size="20" :stroke-width="2" />
      </button>

      <div class="tb-breadcrumb">
        <span class="tb-page-title">{{ pageTitle }}</span>
        <span v-if="pageSubtitle" class="tb-page-sub">{{ pageSubtitle }}</span>
      </div>
    </div>

    <!-- Right: actions -->
    <div class="tb-right">
      <!-- Notifications bell -->
      <div ref="notifRef" class="tb-action-wrap">
        <button
          class="tb-action-btn"
          :class="{ 'has-notif': alertCount > 0 }"
          :title="$t('topbar.notifications')"
          @click="toggleNotifPanel"
        >
          <Bell :size="18" :stroke-width="1.8" />
          <span v-if="alertCount > 0" class="tb-badge">
            {{ alertCount > 9 ? '9+' : alertCount }}
          </span>
        </button>

        <Teleport to="body">
          <transition name="tb-dd">
            <div v-if="showNotifPanel" class="tb-notif-dropdown" :style="notifDdPos" @click.stop>
              <div class="tb-notif-header">
                <span>{{ $t('topbar.notifications') }}</span>
              </div>
              <div class="tb-notif-list">
                <p v-if="recentAlerts.length === 0" class="tb-notif-empty">
                  {{ $t('topbar.noNotifications') }}
                </p>
                <div
                  v-for="a in recentAlerts"
                  :key="a.id || a.date"
                  class="tb-notif-item"
                  :class="{
                    unread: !isAlertSeen(a),
                    'tb-notif-item--chat': a.kind === 'chat_report',
                  }"
                >
                  <div class="tb-notif-content">
                    <p class="tb-notif-text">
                      <span v-if="a.kind === 'chat_report'" class="tb-notif-pill">CHAT</span>
                      {{ a.name }}
                    </p>
                    <p v-if="a.author_name" class="tb-notif-date">
                      — {{ a.author_name }} · {{ formatDate(a.date) }}
                    </p>
                    <p v-else class="tb-notif-date">{{ formatDate(a.date) }}</p>
                    <div v-if="a.kind === 'chat_report'" class="tb-notif-actions">
                      <button class="tb-notif-act" @click.stop="dismissChatReport(a)">
                        {{ $t('requestsAdmin.chatReport.dismiss') }}
                      </button>
                      <button
                        v-if="!a.message_deleted"
                        class="tb-notif-act tb-notif-act--danger"
                        @click.stop="deleteChatMessage(a)"
                      >
                        {{ $t('requestsAdmin.chatReport.delete') }}
                      </button>
                    </div>
                  </div>
                  <span v-if="!isAlertSeen(a)" class="tb-notif-dot" />
                </div>
              </div>
            </div>
          </transition>
        </Teleport>
      </div>

      <!-- User avatar dropdown -->
      <div ref="userRef" class="tb-action-wrap">
        <button class="tb-user-btn" @click="showUserMenu = !showUserMenu">
          <span class="tb-avatar">{{ userInitial }}</span>
          <span class="tb-username">{{ username }}</span>
          <ChevronDown
            class="tb-chevron"
            :class="{ open: showUserMenu }"
            :size="12"
            :stroke-width="2.5"
          />
        </button>

        <Teleport to="body">
          <transition name="tb-dd">
            <div v-if="showUserMenu" class="tb-user-dropdown" :style="userDdPos" @click.stop>
              <div class="tb-user-header">
                <span class="tb-avatar tb-avatar-lg">{{ userInitial }}</span>
                <div>
                  <p class="tb-user-name">{{ username }}</p>
                  <p class="tb-user-role">{{ $t('common.administrator') }}</p>
                </div>
              </div>
              <div class="tb-user-sep" />
              <div class="tb-accent-section">
                <span class="tb-accent-label">{{ $t('settings.accentColor') }}</span>
                <div class="tb-accent-row">
                  <button
                    v-for="preset in accentPresets"
                    :key="preset.name"
                    class="tb-accent-dot"
                    :class="{ active: preset.name === accentName }"
                    :style="{ background: preset.color }"
                    :title="preset.name"
                    @click="setAccent(preset.name)"
                  />
                </div>
              </div>
              <div class="tb-user-sep" />
              <button class="tb-user-item" @click="handleLogout">
                <LogOut :size="16" :stroke-width="1.8" />
                <span>{{ t('topbar.logout') }}</span>
              </button>
            </div>
          </transition>
        </Teleport>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { useTheme } from '@/composables/useTheme'
import { useTopbarAlerts } from '@/composables/useTopbarAlerts'
import { Bell, ChevronDown, LogOut, Menu } from 'lucide-vue-next'
import '@/assets/styles/app-topbar.css'
import '@/assets/styles/app-topbar-dropdowns.css'

const emit = defineEmits(['toggleMobile'])

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { user, logout } = useAuth()
const { accentName, accentPresets, setAccent } = useTheme()

const {
  alertCount,
  recentAlerts,
  dismissChatReport,
  deleteChatMessage,
  isAlertSeen,
  markAllRead,
  formatDate,
} = useTopbarAlerts()

const showNotifPanel = ref(false)
const showUserMenu = ref(false)
const notifRef = ref(null)
const userRef = ref(null)
const notifDdPos = ref({})
const userDdPos = ref({})

const username = computed(() => user.value?.username || '')
const userInitial = computed(() => (username.value || '?')[0].toUpperCase())
const pageTitle = computed(() => {
  if (route.meta?.titleKey) return t(route.meta.titleKey)
  return route.meta?.title || t('sidebar.dashboard')
})
const pageSubtitle = computed(() => {
  if (route.meta?.subtitleKey) return t(route.meta.subtitleKey)
  return route.meta?.subtitle || ''
})

function positionDropdown(refEl, posRef) {
  if (!refEl.value) return
  const rect = refEl.value.getBoundingClientRect()
  posRef.value = {
    position: 'fixed',
    top: rect.bottom + 8 + 'px',
    right: window.innerWidth - rect.right + 'px',
    zIndex: 9999,
  }
}

function onClickOutside(e) {
  if (notifRef.value && !notifRef.value.contains(e.target)) {
    const dd = document.querySelector('.tb-notif-dropdown')
    if (dd && dd.contains(e.target)) return
    showNotifPanel.value = false
  }
  if (userRef.value && !userRef.value.contains(e.target)) {
    const dd = document.querySelector('.tb-user-dropdown')
    if (dd && dd.contains(e.target)) return
    showUserMenu.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    showNotifPanel.value = false
    showUserMenu.value = false
  }
}

watch(showNotifPanel, v => {
  if (v) positionDropdown(notifRef, notifDdPos)
})
watch(showUserMenu, v => {
  if (v) positionDropdown(userRef, userDdPos)
})

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
  document.removeEventListener('keydown', onKeydown)
})

function toggleNotifPanel() {
  showNotifPanel.value = !showNotifPanel.value
  // Opening the panel is the read action — clears the badge and
  // flags every listed alert on the server.
  if (showNotifPanel.value && alertCount.value > 0) markAllRead()
}

async function handleLogout() {
  showUserMenu.value = false
  await logout()
  router.push({ name: 'login', query: { logged_out: '1' } })
}
</script>
