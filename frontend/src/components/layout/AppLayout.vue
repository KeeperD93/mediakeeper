<template>
  <a href="#main-content" class="mk-skip-link">{{ $t('common.skipToMain') }}</a>
  <div class="mk-app-shell flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <AppSidebar
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileMenuOpen"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
      @close-mobile="mobileMenuOpen = false"
      @open-search="showSearch = true"
    />

    <!-- Zone principale -->
    <main id="main-content" tabindex="-1" class="mk-app-main flex-1 flex flex-col overflow-hidden min-w-0">
      <!-- Persistent deployment-misconfiguration banner -->
      <DeploymentBanner />

      <!-- Topbar -->
      <AppTopbar @toggle-mobile="mobileMenuOpen = !mobileMenuOpen" />

      <!-- Contenu page -->
      <div class="mk-app-content flex-1 overflow-y-scroll">
        <router-view v-slot="{ Component, route }">
          <transition name="route-slide" mode="out-in">
            <keep-alive :include="['DashboardView', 'StatsView', 'WatchlistView']">
              <component :is="Component" :key="route.name" />
            </keep-alive>
          </transition>
        </router-view>
        <AttributionFooter class="mk-app-attribution" />
      </div>
    </main>
  </div>

  <!-- Search modal (Cmd+K) -->
  <SearchModal :visible="showSearch" @close="showSearch = false" />

  <!-- Forced password change modal -->
  <ForcePasswordModal v-if="mustChangePassword" />

  <!-- Onboarding wizard -->
  <OnboardingWizard ref="onboardingRef" @done="onOnboardingDone" />

  <!-- What's new popup (after update) -->
  <WhatsNewModal />
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
import DeploymentBanner from './DeploymentBanner.vue'
import AttributionFooter from '@/components/common/AttributionFooter.vue'
import SearchModal from '@/components/SearchModal.vue'
import ForcePasswordModal from '@/components/ForcePasswordModal.vue'
import OnboardingWizard from '@/components/OnboardingWizard.vue'
import WhatsNewModal from '@/components/WhatsNewModal.vue'
import { useAuth } from '@/composables/useAuth'
import { useKonamiCode } from '@/composables/useKonamiCode'
import { useTheme } from '@/composables/useTheme'

const { mustChangePassword, startTokenRefresh } = useAuth()
const onboardingRef = ref(null)
function onOnboardingDone() {
  /* dashboard already accessible */
}
const { syncFromServer } = useTheme()

// Konami code ↑↑↓↓←→←→BA
useKonamiCode()

const sidebarCollapsed = ref(false)
const mobileMenuOpen = ref(false)
const showSearch = ref(false)

// Restore the sidebar state
const savedCollapsed = localStorage.getItem('mk_sidebar_collapsed')
if (savedCollapsed === 'true') sidebarCollapsed.value = true

// Persister
watch(sidebarCollapsed, v => {
  localStorage.setItem('mk_sidebar_collapsed', v ? 'true' : 'false')
})

// Cmd+K / Ctrl+K global search shortcut
function onGlobalKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    showSearch.value = !showSearch.value
  }
}

onMounted(() => {
  startTokenRefresh()
  syncFromServer() // Load theme/accent from the user DB
  document.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<style>
/* Global mobile safeties for the admin shell.
   - overflow-x: clip on the root blocks rogue overflow from forcing
     the mobile viewport to zoom out.
   - overflow-x: auto on the content lets individual pages declare
     horizontal scrollers (tables, carousels) without leaking to the
     outer viewport.
   - -webkit-tap-highlight-color neutralises the grey flash on tap.
   - overscroll-behavior disables the iOS pull-to-refresh on the main
     scroll container so admin tables don't accidentally reload. */
.mk-app-shell {
  background: var(--bg-primary);
  /* `clip` instead of `hidden`: prevents horizontal overflow without
     promoting the shell to a scroll container, which would swallow the
     document's vertical scroll on long pages. */
  overflow-x: clip;
  -webkit-tap-highlight-color: transparent;
}
.mk-app-content {
  background: var(--bg-primary);
  overscroll-behavior-y: contain;
}
@media (max-width: 767px) {
  .mk-app-content {
    padding-bottom: env(safe-area-inset-bottom, 0);
  }
}
</style>
