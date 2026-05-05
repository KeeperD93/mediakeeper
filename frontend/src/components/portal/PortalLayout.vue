<template>
  <div class="pt-layout">
    <PortalNav
      :active-tab="activeTab"
      :profile="profile"
      :is-admin="isAdmin"
      :has-backoffice-access="hasBackofficeAccess"
      :show-requests-tab="showRequestsTab"
      @navigate="onNavigate"
      @open-whats-new="onOpenWhatsNew"
      @open-daily-digest="onOpenDailyDigest"
      @open-help="onOpenHelp"
    />

    <main class="pt-main">
      <router-view />
      <AttributionFooter class="pt-attribution" />
    </main>

    <PortalBottomNav
      :active-tab="activeTab"
      :show-requests-tab="showRequestsTab"
      @navigate="onNavigate"
    />

    <!-- Floating action cluster (chat / surprise / promotion). The chat
         panel is mounted from inside the FAB so we only instantiate it
         once per layout and keep the singleton websocket happy. -->
    <HomeFab @open-surprise="surpriseOpen = true" />

    <SurpriseOverlay v-if="surpriseOpen" @close="surpriseOpen = false" />

    <NewsPopup v-if="showNewsPopup" :items="unreadNews" @dismiss="dismissNews" />

    <!-- GDPR opt-in: persistent grace-period banner shown on every page
         while a deletion request is pending. EventBanner stacks below
         it so neither hides the other. -->
    <DeletionPendingBanner />

    <!-- Top scrolling banner for upcoming events I'm part of. -->
    <EventBanner />

    <!-- "What's new" popup for the Portal viewer (auto-shows once per version,
         can also be manually re-opened from the avatar menu). -->
    <PortalWhatsNewModal :open="whatsNewOpen" @close="whatsNewOpen = false" />

    <!-- Daily digest overlay: auto-opens once per calendar day when there is
         content to show, can also be re-opened manually from the avatar menu. -->
    <PortalDailyDigestOverlay :open="dailyDigestOpen" @close="dailyDigestOpen = false" />

    <!-- Help center overlay — opened from the avatar menu. Lazy-rendered:
         the heavy article body / sanitised HTML is only fetched when the
         overlay is first opened. -->
    <PortalHelpOverlay :open="helpOpen" @close="helpOpen = false" />

    <!-- Blocking modal that fires once per account: forces the user to pick
         a real username on first portal login. ``display_name_must_set``
         flips to false the moment they save. -->
    <ForceUsernameModal :open="forceUsernameOpen" @done="forceUsernameOpen = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { usePortalNews } from '@/composables/portal/usePortalNews'
import { usePortalLocale } from '@/composables/portal/usePortalLocale'
import { usePortalChat } from '@/composables/portal/usePortalChat'
import AttributionFooter from '@/components/common/AttributionFooter.vue'
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
const forceUsernameOpen = ref(false)
// Latches the first time we open the modal so subsequent profile saves
// (e.g. saving favorite genres while ``must_set`` is still true on the
// backend until the username is actually picked) don't re-pop it. The
// user has explicit access via /portal/settings → Identity if they
// want to set their username later in the session.
let forceUsernameShownOnce = false

watch(
  () => [profile.value?.display_name_must_set, profile.value?.role],
  ([must, role]) => {
    if (role === USER_ROLE.ADMIN) return
    if (must && !forceUsernameShownOnce) {
      forceUsernameOpen.value = true
      forceUsernameShownOnce = true
    }
  },
  { immediate: true },
)

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
  if (unreadNews.value.length > 0) {
    showNewsPopup.value = true
  }
})
</script>

<style scoped>
.pt-layout {
  min-height: 100vh;
  background: var(--bg-primary);
  color: #fff;
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
}
/* All portal pages get nav clearance. The home hero handles it
   by being tall enough (90vh) to extend behind the nav. */
.pt-main > :deep(*) {
  padding-top: 112px;
}
/* Home page hero already fills the space, override */
.pt-main > :deep(.pt-home),
.pt-main > :deep(.vmd2-root) {
  padding-top: 0;
}
/* The attribution sits at the bottom of the column: it must not
   inherit the top clearance meant for routed page content. */
.pt-main > .pt-attribution {
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

  /* Keep the bottom-nav clearance, drop the unwanted top clearance. */
  .pt-main > .pt-attribution {
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

  .pt-main > .pt-attribution {
    padding-top: 0;
  }
}
</style>
