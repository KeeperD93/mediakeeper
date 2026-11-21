<template>
  <a href="#main-content" class="mk-skip-link">{{ $t('common.skipToMain') }}</a>
  <div class="pt-layout" :class="{ 'pt-layout--bare': isMaintenancePage }">
    <PortalNav
      v-if="!isMaintenancePage"
      :active-tab="activeTab"
      :profile="profile"
      :is-admin="isAdmin"
      :has-backoffice-access="hasBackofficeAccess"
      :show-requests-tab="showRequestsTab"
      :donation="ui.donation"
      @navigate="onNavigate"
      @open-daily-digest="onOpenDailyDigest"
      @open-help="onOpenHelp"
    />

    <main id="main-content" tabindex="-1" class="pt-main">
      <router-view />
    </main>

    <PortalBottomNav
      v-if="!isMaintenancePage"
      :active-tab="activeTab"
      :show-requests-tab="showRequestsTab"
      @navigate="onNavigate"
    />

    <!-- Floating action cluster (chat / surprise / promotion). The chat
         panel is mounted from inside the FAB so we only instantiate it
         once per layout and keep the singleton websocket happy.
         Hidden while the first-login wizard is due so nobody drops into
         chat before choosing a name. -->
    <HomeFab v-if="!wizardMode && !isMaintenancePage" @open-surprise="surpriseOpen = true" />

    <SurpriseOverlay v-if="surpriseOpen" @close="surpriseOpen = false" />

    <!-- GDPR opt-in: persistent grace-period banner shown on every page
         while a deletion request is pending. EventBanner stacks below
         it so neither hides the other. -->
    <DeletionPendingBanner v-if="!isMaintenancePage" />

    <!-- Top scrolling banner for upcoming events I'm part of. -->
    <EventBanner v-if="!isMaintenancePage" />

    <!-- Daily digest overlay: auto-opens once per calendar day when there is
         content to show, can also be re-opened manually from the avatar menu.
         It carries the news and the new Portal version too, so neither pops up
         on its own. While the first-login wizard is due it waits, then opens
         right after it, in the same frame, even with nothing new. -->
    <PortalDailyDigestOverlay
      v-if="!wizardMode && !isMaintenancePage"
      :open="dailyDigestOpen"
      :auto="!wizardShownThisVisit"
      :chained="digestChained"
      @close="onDigestClose"
    />

    <!-- Help center overlay — opened from the avatar menu. Lazy-rendered:
         the heavy article body / sanitised HTML is only fetched when the
         overlay is first opened. -->
    <PortalHelpOverlay v-if="!isMaintenancePage" :open="helpOpen" @close="helpOpen = false" />

    <!-- First-login wizard, blocking: the whole tour once per account
         (``onboarding_pending``), the name alone after an admin reset it
         (``display_name_must_set``). The server's flags are the only truth:
         its final save clears them, and the wizard hands over to the digest. -->
    <PortalOnboardingWizard
      v-if="wizardShown"
      :key="wizardMode"
      :mode="wizardMode"
      @done="onWizardDone"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { usePortalLocale } from '@/composables/portal/usePortalLocale'
import { usePortalChat } from '@/composables/portal/usePortalChat'
import PortalNav from './PortalNav.vue'
import PortalBottomNav from './PortalBottomNav.vue'
import HomeFab from './HomeFab.vue'
import SurpriseOverlay from './SurpriseOverlay.vue'
import EventBanner from './EventBanner.vue'
import DeletionPendingBanner from './DeletionPendingBanner.vue'
import PortalDailyDigestOverlay from './PortalDailyDigestOverlay.vue'
import PortalHelpOverlay from './PortalHelpOverlay.vue'
import PortalOnboardingWizard from './wizard/PortalOnboardingWizard.vue'
import { USER_ROLE } from '@/constants/auth'
import { PORTAL_TAB } from '@/constants/portal'
import { WIZARD_MODE } from '@/constants/portalOnboarding'

const route = useRoute()
const router = useRouter()
const { profile, ui, checkPortalAuth } = usePortalAuth()
const { applyPortalLocale, restoreGlobalLocale } = usePortalLocale()
const { initGlobalChat, shutdownGlobalChat } = usePortalChat()

// Apply the viewer's effective portal language (their explicit pick, or the
// instance default when they inherit) as soon as the profile loads, and react
// to live profile/settings updates.
watch(
  () => profile.value?.effective_language,
  lang => {
    if (lang) applyPortalLocale(lang)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  // Leaving the Portal: restore the global MediaKeeper locale.
  restoreGlobalLocale()
  // Tear down the persistent chat websocket so we don't leak it onto
  // pages outside the portal.
  shutdownGlobalChat()
})

// Boot the persistent chat as soon as the profile is known. Re-runs if
// the profile is replaced (account switch).
watch(
  () => profile.value?.user_id || profile.value?.id || null,
  uid => {
    if (uid) initGlobalChat(profile.value)
  },
  { immediate: true },
)

const surpriseOpen = ref(false)
const dailyDigestOpen = ref(false)
// The digest opens in the wizard's frame: no fade of the backdrop, the window rises.
const digestChained = ref(false)
const helpOpen = ref(false)

function onOpenDailyDigest() {
  dailyDigestOpen.value = true
}

function onDigestClose() {
  dailyDigestOpen.value = false
  digestChained.value = false
}

function onWizardDone() {
  // A name chosen on the maintenance page: the digest waits for the portal to open,
  // then rises as usual, out of the wizard's frame.
  digestChained.value = !isMaintenancePage.value
  dailyDigestOpen.value = true
}

function onOpenHelp() {
  helpOpen.value = true
}

const activeTab = computed(() => route.name || PORTAL_TAB.HOME)
const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)
// First-login gate: the whole tour once per account, admins included; else the
// name alone when an admin reset it (never owed by an admin). Until it is done,
// nothing else opens by itself and the FAB stays hidden.
const wizardMode = computed(() => {
  if (profile.value?.onboarding_pending) return WIZARD_MODE.FULL
  if (!isAdmin.value && profile.value?.display_name_must_set) return WIZARD_MODE.RESET
  return null
})
// The wizard opens the digest itself when it ends: the digest does not look for
// content on its own during that visit.
const wizardShownThisVisit = ref(!!wizardMode.value)
watch(wizardMode, mode => {
  if (mode) wizardShownThisVisit.value = true
})
// Maintenance lockdown: non-admins are redirected here by the router guard.
// Hide the whole portal chrome (nav, FAB, banners, auto-popping overlays) so
// only the holding page — and a name owed after a reset — remain. The tour
// waits for the portal to open again.
const isMaintenancePage = computed(() => route.name === 'portal-maintenance')
const wizardShown = computed(
  () => wizardMode.value === WIZARD_MODE.RESET || (!!wizardMode.value && !isMaintenancePage.value),
)
// Backoffice access is its own gate: a Portal moderator (role=admin)
// is not necessarily a backoffice operator. Imported Emby accounts
// always fail the backoffice login because their stored hash is the
// Emby-only sentinel — hiding the Dashboard shortcut for them avoids
// the "click → 401 → bounce back" loop.
const hasBackofficeAccess = computed(() => !!profile.value?.has_backoffice_access)
// Admin-only surface now: the requests tab is the moderation
// screen (approve/reject/delete). Regular viewers no longer see it.
const showRequestsTab = computed(() => isAdmin.value)

watch(
  [activeTab, showRequestsTab],
  ([tab, canSeeRequests]) => {
    if (!canSeeRequests && tab === PORTAL_TAB.REQUESTS) {
      router.replace({ name: PORTAL_TAB.HOME })
    }
  },
  { immediate: true },
)

function onNavigate(name) {
  router.push({ name })
}

onMounted(() => {
  checkPortalAuth()
})
</script>

<style scoped>
.pt-layout {
  min-height: 100vh;
  background: var(--portal-bg-primary);
  color: var(--portal-text-primary);
  -webkit-tap-highlight-color: transparent;
  overscroll-behavior-y: contain;
  /* Safety net: any descendant absolute/fixed/translated element that
     accidentally renders off-screen (decorative FX, sidebar godrays
     on wide-data profiles, long labels without ellipsis) must NOT
     push the viewport. Without this, mobile browsers auto-zoom-out
     to fit the overflow — making every section look truncated.
     IMPORTANT: use `overflow-x: clip` not `hidden`. `hidden` implicitly
     promotes the element to a scroll container (overflow-y becomes auto),
     which on long pages steals the vertical scroll from the document
     and locks the layout. `clip` just clips without creating a scroll
     context — the document keeps scrolling normally. */
  overflow-x: clip;
}
.pt-main {
  min-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}
/* All portal pages get nav clearance. The home hero handles it
   by being tall enough (90vh) to extend behind the nav. */
.pt-main > :deep(*) {
  flex: 1 1 auto;
  padding-top: 112px;
}
/* Home page hero already fills the space, override */
.pt-main > :deep(.pt-home),
.pt-main > :deep(.vmd2-root) {
  padding-top: 0;
}

/* Maintenance holding page renders without the top nav, so drop the nav
   clearance — the card centres in the full viewport. */
.pt-layout--bare .pt-main > :deep(*) {
  padding-top: 0;
}

/* Mobile: the tabs row is hidden from the top bar (handled by the
   PortalBottomNav). That lets us claim the 112 → 76 top clearance,
   and we reserve space at the bottom for the fixed tab bar + iPhone
   home indicator safe-area. */
@media (max-width: 767px) {
  .pt-main > :deep(*) {
    padding-top: 76px;
    padding-bottom: calc(72px + env(safe-area-inset-bottom, 0px));
  }

  .pt-main > :deep(.pt-home),
  .pt-main > :deep(.vmd2-root) {
    padding-top: 0;
    padding-bottom: calc(72px + env(safe-area-inset-bottom, 0px));
  }
}

/* Roomy desktop: the single-row top bar measures ~71px. 96px padding-top
   keeps a 25px breathing strip while reclaiming above-the-fold space the
   default 112px wasted on common laptop viewports such as 1366×768. */
@media (min-width: 1024px) {
  .pt-main > :deep(*) {
    padding-top: 96px;
  }

  .pt-main > :deep(.pt-home),
  .pt-main > :deep(.vmd2-root) {
    padding-top: 0;
  }
}
</style>
