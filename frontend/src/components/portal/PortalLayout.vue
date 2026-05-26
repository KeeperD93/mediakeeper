<template>
  <a href="#main-content" class="mk-skip-link">{{ $t('common.skipToMain') }}</a>
  <div class="pt-layout">
    <PortalNav
      :active-tab="activeTab"
      :profile="profile"
      :is-admin="isAdmin"
      :has-backoffice-access="hasBackofficeAccess"
      :show-requests-tab="showRequestsTab"
      support-url="https://ko-fi.com/keeperd93"
      @navigate="onNavigate"
      @open-whats-new="onOpenWhatsNew"
      @open-daily-digest="onOpenDailyDigest"
      @open-help="onOpenHelp"
    />

    <main id="main-content" tabindex="-1" class="pt-main">
      <router-view />
    </main>

    <PortalBottomNav
      :active-tab="activeTab"
      :show-requests-tab="showRequestsTab"
      @navigate="onNavigate"
    />

    <!-- Floating action cluster (chat / surprise / promotion). The chat
         panel is mounted from inside the FAB so we only instantiate it
         once per layout and keep the singleton websocket happy.
         Hidden while the user owes us a display name so they can't drop
         into chat under their pre-reset alias. -->
    <HomeFab v-if="!mustPickUsername" @open-surprise="surpriseOpen = true" />

    <SurpriseOverlay v-if="surpriseOpen" @close="surpriseOpen = false" />

    <!-- Auto-opening overlays are gated behind ``mustPickUsername``: when
         the admin reset a viewer's display name, ForceUsernameModal must
         stay the topmost layer until they pick a new one, otherwise the
         What's-new and Daily-digest popups (whose z-index is higher than
         the portal overlay token) paint over the picker and trap them. -->
    <NewsPopup
      v-if="showNewsPopup && !mustPickUsername"
      :items="unreadNews"
      @dismiss="dismissNews"
    />

    <!-- GDPR opt-in: persistent grace-period banner shown on every page
         while a deletion request is pending. EventBanner stacks below
         it so neither hides the other. -->
    <DeletionPendingBanner />

    <!-- Top scrolling banner for upcoming events I'm part of. -->
    <EventBanner />

    <!-- "What's new" popup for the Portal viewer (auto-shows once per version,
         can also be manually re-opened from the avatar menu). -->
    <PortalWhatsNewModal
      v-if="!mustPickUsername"
      :open="whatsNewOpen"
      @close="whatsNewOpen = false"
    />

    <!-- Daily digest overlay: auto-opens once per calendar day when there is
         content to show, can also be re-opened manually from the avatar menu. -->
    <PortalDailyDigestOverlay
      v-if="!mustPickUsername"
      :open="dailyDigestOpen"
      @close="dailyDigestOpen = false"
    />

    <!-- Help center overlay — opened from the avatar menu. Lazy-rendered:
         the heavy article body / sanitised HTML is only fetched when the
         overlay is first opened. -->
    <PortalHelpOverlay :open="helpOpen" @close="helpOpen = false" />

    <!-- Blocking modal mounted via v-if so the picker is GUARANTEED to be
         visible whenever ``mustPickUsername`` is true: the modal arms in
         its onMounted hook with ``props.open=true``, no transition watcher
         needed and no chance of a stuck visibility latch (the previous
         :open binding could race with profile arrival on a fresh F5). The
         backend ``display_name_must_set`` flag is the single source of
         truth and only flips back to false on a saved display name. -->
    <ForceUsernameModal v-if="mustPickUsername" :open="true" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { usePortalNews } from '@/composables/portal/usePortalNews'
import { usePortalLocale } from '@/composables/portal/usePortalLocale'
import { usePortalChat } from '@/composables/portal/usePortalChat'
import PortalNav from './PortalNav.vue'
import PortalBottomNav from './PortalBottomNav.vue'
import HomeFab from './HomeFab.vue'
import SurpriseOverlay from './SurpriseOverlay.vue'
import NewsPopup from './NewsPopup.vue'
import EventBanner from './EventBanner.vue'
import DeletionPendingBanner from './DeletionPendingBanner.vue'
import PortalWhatsNewModal from './PortalWhatsNewModal.vue'
import PortalDailyDigestOverlay from './PortalDailyDigestOverlay.vue'
import PortalHelpOverlay from './PortalHelpOverlay.vue'
import ForceUsernameModal from './settings/ForceUsernameModal.vue'
import { USER_ROLE } from '@/constants/auth'
import { PORTAL_TAB } from '@/constants/portal'

const route = useRoute()
const router = useRouter()
const { profile, checkPortalAuth } = usePortalAuth()
const { unreadNews, fetchUnread, markRead } = usePortalNews()
const { applyPortalLocale, restoreGlobalLocale } = usePortalLocale()
const { initGlobalChat, shutdownGlobalChat } = usePortalChat()

// Apply the user's Portal-preferred language as soon as the profile is loaded,
// and react to live changes from profile/settings updates.
watch(
  () => profile.value?.language,
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

const showNewsPopup = ref(false)
const surpriseOpen = ref(false)
const whatsNewOpen = ref(false)
const dailyDigestOpen = ref(false)
const helpOpen = ref(false)

function onOpenWhatsNew() {
  whatsNewOpen.value = true
}

function onOpenDailyDigest() {
  dailyDigestOpen.value = true
}

function onOpenHelp() {
  helpOpen.value = true
}

const activeTab = computed(() => route.name || PORTAL_TAB.HOME)
const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)
// Pre-pseudo gate: viewers whose ``display_name_must_set`` flag is on
// (first login or admin-triggered reset) must clear the picker before
// they can use anything else. Drives both the blocking ForceUsernameModal
// and the v-if guards on the auto-popping overlays / FAB.
const mustPickUsername = computed(() => !isAdmin.value && !!profile.value?.display_name_must_set)
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

async function dismissNews() {
  for (const n of unreadNews.value) {
    await markRead(n.id, true)
  }
  showNewsPopup.value = false
}

onMounted(async () => {
  await checkPortalAuth()
  await fetchUnread()
  if (unreadNews.value.length > 0 && !mustPickUsername.value) {
    showNewsPopup.value = true
  }
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

/* Legacy narrow-desktop layout (tabs wrap to 2nd row in top bar) */
@media (min-width: 768px) and (max-width: 920px) {
  .pt-main > :deep(*) {
    padding-top: 168px;
  }

  .pt-main > :deep(.pt-home),
  .pt-main > :deep(.vmd2-root) {
    padding-top: 0;
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
