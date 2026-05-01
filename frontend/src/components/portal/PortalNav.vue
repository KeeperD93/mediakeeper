<template>
  <nav ref="navRef" class="pt-nav" :class="{ 'pt-nav--solid': scrolled }">
    <div class="pt-nav-inner">
      <button class="pt-nav-brand" type="button" @click="navigateTo(PORTAL_TAB.HOME)">
        <img src="/assets/icons/mediakeeper.png" :alt="$t('portal.nav.brand')" class="pt-brand-img" />
        <span class="pt-brand-text">{{ $t('portal.nav.brand') }}</span>
      </button>

      <div class="pt-nav-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.name"
          class="pt-tab"
          :class="{ 'pt-tab--active': isTabActive(tab.name) }"
          type="button"
          @click="navigateTo(tab.name)"
        >
          {{ $t(tab.label) }}
        </button>
      </div>

      <PortalSearchBox class="pt-nav-search" />

      <div class="pt-nav-quick">
        <!-- Compact search trigger — shown at narrow widths where the
             full input would overflow the topbar grid. Toggles
             `searchDrawerOpen` and renders the search box as a
             full-width drawer under the topbar. -->
        <button
          class="pt-nav-icon pt-nav-search-trigger"
          type="button"
          :title="$t('portal.search.submit')"
          :aria-label="$t('portal.search.submit')"
          @click="toggleSearchDrawer"
        >
          <Search :size="20" />
        </button>

        <button
          v-if="isAdmin"
          class="pt-nav-icon pt-nav-icon--heart"
          :class="{ 'pt-nav-icon--disabled': !supportUrl }"
          type="button"
          :title="supportTitle"
          :aria-label="supportTitle"
          :disabled="!supportUrl"
          @click="openSupport"
        >
          <Heart :size="20" fill="currentColor" stroke="currentColor" :stroke-width="1.5" />
        </button>

        <button
          class="pt-nav-icon pt-nav-icon--lists"
          type="button"
          :title="$t('portal.lists.navLabel')"
          :aria-label="$t('portal.lists.navLabel')"
          @click="goToLists"
        >
          <Library :size="20" stroke-width="1.8" />
        </button>

        <CalendarButton ref="calendarRef" />
        <NotificationBell />

        <button
          v-if="hasBackofficeAccess"
          class="pt-nav-icon pt-nav-icon--dashboard"
          type="button"
          :title="$t('portal.tabs.dashboard')"
          :aria-label="$t('portal.tabs.dashboard')"
          @click="goToDashboard"
        >
          <Home :size="20" />
        </button>

        <div ref="menuRef" class="pt-avatar-menu">
          <button
            class="pt-avatar-trigger"
            type="button"
            :title="$t('portal.avatar.menu')"
            :aria-label="$t('portal.avatar.menu')"
            @click="toggleMenu"
          >
            <img
              v-if="profile?.avatar_url"
              :src="profile.avatar_url"
              :alt="profile.display_name"
              class="pt-avatar-img"
            />
            <span v-else class="pt-avatar-placeholder">
              {{ avatarInitial }}
            </span>
            <ChevronDown class="pt-avatar-chevron" :size="14" :stroke-width="2.2" />
          </button>

          <transition name="pt-avatar-pop">
            <div v-if="menuOpen" class="pt-avatar-pop">
              <div class="pt-avatar-pop-head">
                <span class="pt-avatar-pop-name">{{ profile?.display_name || $t('portal.avatar.account') }}</span>
                <span class="pt-avatar-pop-role">{{ roleLabel }}</span>
              </div>

              <!-- Mobile-only entries: on narrow screens the top bar keeps
                   only search + bell + avatar, so these shortcuts that
                   normally live as icons move into the avatar menu. -->
              <button
                v-if="hasBackofficeAccess"
                class="pt-avatar-pop-item pt-avatar-pop-item--mobile"
                type="button"
                @click="goToDashboard"
              >
                {{ $t('portal.avatar.dashboard') }}
              </button>

              <button
                class="pt-avatar-pop-item pt-avatar-pop-item--mobile"
                type="button"
                @click="goToLists"
              >
                {{ $t('portal.avatar.lists') }}
              </button>

              <button
                class="pt-avatar-pop-item pt-avatar-pop-item--mobile"
                type="button"
                @click="openCalendarFromMenu"
              >
                {{ $t('portal.avatar.calendar') }}
              </button>

              <button class="pt-avatar-pop-item" type="button" @click="goToSettings">
                {{ $t('portal.avatar.settings') }}
              </button>

              <button class="pt-avatar-pop-item" type="button" @click="goToMyTickets">
                {{ $t('portal.avatar.myTickets') }}
              </button>

              <button class="pt-avatar-pop-item" type="button" @click="openDailyDigest">
                {{ $t('portal.avatar.dailyDigest') }}
              </button>

              <button class="pt-avatar-pop-item" type="button" @click="openHelp">
                {{ $t('portal.avatar.help') }}
              </button>

              <button class="pt-avatar-pop-item" type="button" @click="openWhatsNew">
                {{ $t('portal.avatar.whatsNew') }}
              </button>

              <button class="pt-avatar-pop-item pt-avatar-pop-item--danger" type="button" @click="doLogout">
                {{ $t('portal.avatar.logout') }}
              </button>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <!-- Collapsed search drawer — full-width panel under the topbar.
         Rendered only in the compact breakpoint via CSS; the prop on
         the nav toggles its `open` class so the CSS transition runs. -->
    <transition name="pt-search-drawer">
      <div v-if="searchDrawerOpen" class="pt-nav-search-drawer" @click.self="searchDrawerOpen = false">
        <PortalSearchBox class="pt-nav-search-drawer-box" />
      </div>
    </transition>
  </nav>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import NotificationBell from './NotificationBell.vue'
import CalendarButton from './CalendarButton.vue'
import PortalSearchBox from './PortalSearchBox.vue'
import { ChevronDown, Heart, Home, Library, Search } from 'lucide-vue-next'
import { usePortalNav } from './usePortalNav.js'
import { PORTAL_TAB } from '@/constants/portal'

import '@/assets/styles/portal/nav-base.css'
import '@/assets/styles/portal/nav-avatar.css'

const props = defineProps({
  activeTab: { type: String, default: '' },
  profile: { type: Object, default: null },
  isAdmin: { type: Boolean, default: false },
  hasBackofficeAccess: { type: Boolean, default: false },
  showRequestsTab: { type: Boolean, default: true },
  supportUrl: { type: String, default: '' },
})

const emit = defineEmits(['navigate', 'open-whats-new', 'open-daily-digest', 'open-help'])

const {
  navRef, menuRef, menuOpen, scrolled, searchDrawerOpen,
  tabs, avatarInitial, roleLabel, supportTitle,
  toggleSearchDrawer, isTabActive, navigateTo,
  goToDashboard, goToSettings, goToMyTickets,
  toggleMenu, openSupport, doLogout, openWhatsNew, openDailyDigest, openHelp, goToLists,
} = usePortalNav(props, emit)

const calendarRef = ref(null)

// Mobile avatar-menu shortcut — the visible calendar button is hidden
// on phones, so this is how users reach the events popup.
async function openCalendarFromMenu() {
  menuOpen.value = false
  await nextTick()
  calendarRef.value?.open?.()
}
</script>
