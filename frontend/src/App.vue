<template>
  <!-- Reconnect overlay shown when the backend goes down. -->
  <Teleport to="body">
    <transition name="reconnect-fade">
      <div v-if="backendDown" class="reconnect-overlay" role="status" aria-live="polite">
        <div class="reconnect-card">
          <img :src="reconnectLogo" alt="" class="reconnect-logo" />
          <span class="reconnect-spinner" />
          <p class="reconnect-text">{{ $t('login.reconnecting') }}</p>
        </div>
      </div>
    </transition>
  </Teleport>

  <router-view />

  <!-- Global confirm dialog (singleton, driven by useConfirm) -->
  <MkConfirmDialog />

  <!-- Toast global -->
  <Teleport to="body">
    <TransitionGroup
      name="toast"
      tag="div"
      class="mk-toast-container"
      role="region"
      aria-live="polite"
      aria-atomic="false"
      :aria-label="$t('a11y.notifications')"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="mk-toast"
        :class="[toast.type]"
        :role="toast.type === 'err' ? 'alert' : 'status'"
        :aria-live="toast.type === 'err' ? 'assertive' : null"
        @click="removeToast(toast.id)"
      >
        <!-- Header: module name -->
        <div class="mk-toast-header">
          <span class="mk-toast-module">{{ t(toast.module) }}</span>
        </div>
        <div class="mk-toast-divider" />

        <!-- Body: icon | vbar | message -->
        <div class="mk-toast-content">
          <img
            v-if="toast.meta?.thumb"
            :src="toast.meta.thumb"
            class="mk-toast-poster"
            @error="$event => ($event.target.style.display = 'none')"
          />
          <div v-else class="mk-toast-icon">
            <Check v-if="toast.type === 'ok'" :size="16" :stroke-width="2.5" />
            <X v-else-if="toast.type === 'err'" :size="16" :stroke-width="2.5" />
            <TriangleAlert v-else-if="toast.type === 'warn'" :size="16" :stroke-width="2.5" />
            <CirclePlay v-else :size="16" />
          </div>
          <div class="mk-toast-vbar" />
          <div class="mk-toast-body">
            <span class="mk-toast-msg">{{ toast.message }}</span>
            <span v-if="toast.meta?.subtitle" class="mk-toast-sub">{{ toast.meta.subtitle }}</span>
          </div>
        </div>

        <div class="mk-toast-progress" />
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchApiResponse } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/composables/useAuth'
import { useBackendHealth } from '@/composables/useBackendHealth'
import MkConfirmDialog from '@/components/common/MkConfirmDialog.vue'
import { Check, CirclePlay, TriangleAlert, X } from 'lucide-vue-next'
// `?inline` forces Vite to embed the asset as a base64 data URL inside
// the JS bundle so the overlay keeps rendering even when the backend
// (which serves /assets/*) is being rebuilt.
import reconnectLogo from '@/assets/icons/mediakeeper-overlay.png?inline'

import '@/assets/styles/app-shell.css'

const { toasts, removeToast, showToast } = useToast()
const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()
const { logout } = useAuth()

const { backendDown, start, stop } = useBackendHealth({
  fetchApiResponse,
  router,
  logout,
  showToast,
  t,
})

function syncDocumentTitle() {
  let titleKey = route.meta?.titleKey
  if (route.name === 'login') {
    const redirect = typeof route.query?.redirect === 'string' ? route.query.redirect : ''
    if (redirect.startsWith('/portal')) titleKey = 'portalLogin.title'
  }
  const routeTitle = titleKey ? t(titleKey) : route.meta?.title || ''
  document.title = routeTitle ? `MediaKeeper · ${routeTitle}` : 'MediaKeeper'
}

onMounted(() => {
  start()
})

onUnmounted(() => {
  stop()
})

watch(
  [() => route.fullPath, () => route.meta?.title, () => route.meta?.titleKey, () => locale.value],
  syncDocumentTitle,
  { immediate: true },
)
</script>
