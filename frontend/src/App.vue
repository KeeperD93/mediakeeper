<template>
  <!-- Overlay de reconnection when le backend tombe -->
  <Teleport to="body">
    <transition name="reconnect-fade">
      <div v-if="backendDown" class="reconnect-overlay">
        <div class="reconnect-card">
          <img src="/assets/icons/mediakeeper.png" alt="" class="reconnect-logo" />
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
    <TransitionGroup name="toast" tag="div" class="mk-toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="mk-toast"
        :class="[toast.type]"
        @click="removeToast(toast.id)"
      >
        <!-- Header: module name -->
        <div class="mk-toast-header">
          <span class="mk-toast-module">{{ toast.module }}</span>
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
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchApiResponse } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import MkConfirmDialog from '@/components/common/MkConfirmDialog.vue'
import { Check, CirclePlay, TriangleAlert, X } from 'lucide-vue-next'

import '@/assets/styles/app-shell.css'

const { toasts, removeToast } = useToast()
const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()
const backendDown = ref(false)
let healthInterval = null
let failCount = 0

function syncDocumentTitle() {
  let titleKey = route.meta?.titleKey
  if (route.name === 'login') {
    const redirect = typeof route.query?.redirect === 'string' ? route.query.redirect : ''
    if (redirect.startsWith('/portal')) titleKey = 'portalLogin.title'
  }
  const routeTitle = titleKey ? t(titleKey) : route.meta?.title || ''
  document.title = routeTitle ? `MediaKeeper · ${routeTitle}` : 'MediaKeeper'
}

async function checkHealth() {
  // Ne pas checkr sur la page login (elle manages son propre screen de loading)
  if (router.currentRoute.value?.name === 'login') {
    failCount = 0
    backendDown.value = false
    return
  }
  try {
    const res = await fetchApiResponse('/api/health', {
      retryOn401: false,
      redirectOn401: false,
    })
    if (res.ok) {
      if (backendDown.value) {
        backendDown.value = false
        window.location.reload()
      }
      failCount = 0
    } else {
      failCount++
    }
  } catch {
    failCount++
  }
  // Show the overlay after 3 consecutive failures (~15s)
  if (failCount >= 3) backendDown.value = true
}

onMounted(() => {
  healthInterval = setInterval(checkHealth, 5000)
})

onUnmounted(() => {
  if (healthInterval) clearInterval(healthInterval)
})

watch(
  [() => route.fullPath, () => route.meta?.title, () => route.meta?.titleKey, () => locale.value],
  syncDocumentTitle,
  { immediate: true },
)
</script>
