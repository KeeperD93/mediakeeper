<template>
  <aside class="mk-sidebar" :class="{ collapsed, 'mobile-open': mobileOpen }">
    <div class="sb-logo" @click="$router.push('/')">
      <img
        src="/assets/icons/mediakeeper.png"
        alt="MediaKeeper"
        class="sb-logo-img"
        :class="{ 'sb-logo-sm': collapsed }"
      />
      <transition name="sb-fade">
        <span v-if="!collapsed" class="sb-logo-text">MediaKeeper</span>
      </transition>
    </div>

    <button
      class="sb-collapse-btn"
      :class="{ rotated: collapsed }"
      :title="collapsed ? $t('sidebar.expand') : $t('sidebar.collapse')"
      @click="emit('toggle')"
    >
      <ChevronLeft :size="14" />
    </button>

    <div v-if="!collapsed" class="sb-search" @click="emit('openSearch')">
      <Search :size="14" />
      <span class="sb-search-text">{{ $t('common.search') }}</span>
      <kbd class="sb-search-kbd">⌘K</kbd>
    </div>
    <div
      v-else
      class="sb-search-icon"
      :title="$t('search.placeholder') + ' (⌘K)'"
      @click="emit('openSearch')"
    >
      <Search :size="16" />
    </div>

    <nav class="sb-nav">
      <SidebarSection :label="t('sidebar.dashboard')" :collapsed="collapsed" />
      <SidebarLink
        to="/"
        icon="home"
        :label="t('sidebar.dashboard')"
        :collapsed="collapsed"
        :badge="counters.activeSessions"
        :equalizer="true"
        @navigate="closeMobile"
      />

      <SidebarSection :label="t('sidebar.modules')" :collapsed="collapsed" />
      <template v-for="m in moduleEntries" :key="m.to">
        <SidebarLink
          :to="m.to"
          :icon="m.icon"
          :label="t(m.labelKey)"
          :collapsed="collapsed"
          :badge="m.badgeKey ? counters[m.badgeKey] || 0 : 0"
          :badge-color="m.badgeColor"
          :expandable="!collapsed && hasSubTabs(m.to)"
          :expanded="!collapsed && isExpanded(m.to)"
          @navigate="closeMobile"
        />
        <transition name="sb-subtabs">
          <div v-if="!collapsed && isExpanded(m.to)" class="sb-subtabs">
            <SidebarSubLink
              v-for="sub in getSubs(m.to)"
              :key="sub.id"
              :parent-path="m.to"
              :tab-id="sub.id"
              :label="t(sub.labelKey)"
              :icon="sub.icon"
              :default-tab-id="firstTabId(m.to)"
              @navigate="closeMobile"
            />
          </div>
        </transition>
      </template>

      <SidebarSection :label="t('sidebar.requestsSection')" :collapsed="collapsed" />
      <button
        type="button"
        class="sb-link sb-link--action"
        :class="{ collapsed }"
        :title="collapsed ? t('sidebar.requests') : undefined"
        @click="enterRequestsModule"
      >
        <span class="sb-indicator" />
        <span class="sb-icon">
          <MessageSquare :size="20" :stroke-width="1.8" />
        </span>
        <transition name="sb-label">
          <span v-if="!collapsed" class="sb-label-wrap">
            <span class="sb-label">{{ t('sidebar.requests') }}</span>
          </span>
        </transition>
      </button>
      <SidebarLink
        to="/admin/portal/users"
        icon="users"
        :label="t('sidebar.requestsUsers')"
        :collapsed="collapsed"
        @navigate="closeMobile"
      />
      <SidebarLink
        to="/admin/portal"
        icon="settings"
        :label="t('sidebar.requestsAdmin')"
        :collapsed="collapsed"
        exact
        :expandable="!collapsed && hasSubTabs('/admin/portal')"
        :expanded="!collapsed && isExpanded('/admin/portal')"
        @navigate="closeMobile"
      />
      <transition name="sb-subtabs">
        <div v-if="!collapsed && isExpanded('/admin/portal')" class="sb-subtabs">
          <SidebarSubLink
            v-for="sub in getSubs('/admin/portal')"
            :key="sub.id"
            parent-path="/admin/portal"
            :tab-id="sub.id"
            :label="t(sub.labelKey)"
            :icon="sub.icon"
            :default-tab-id="firstTabId('/admin/portal')"
            @navigate="closeMobile"
          />
        </div>
      </transition>

      <SidebarSection :label="t('sidebar.system')" :collapsed="collapsed" />
      <SidebarLink
        to="/settings"
        icon="settings"
        :label="t('sidebar.settings')"
        :collapsed="collapsed"
        :expandable="!collapsed && hasSubTabs('/settings')"
        :expanded="!collapsed && isExpanded('/settings')"
        @navigate="closeMobile"
      />
      <transition name="sb-subtabs">
        <div v-if="!collapsed && isExpanded('/settings')" class="sb-subtabs">
          <SidebarSubLink
            v-for="sub in getSubs('/settings')"
            :key="sub.id"
            parent-path="/settings"
            :tab-id="sub.id"
            :label="t(sub.labelKey)"
            :icon="sub.icon"
            :default-tab-id="firstTabId('/settings')"
            @navigate="closeMobile"
          />
        </div>
      </transition>
      <SidebarLink
        to="/logs"
        icon="logs"
        :label="t('sidebar.logs')"
        :collapsed="collapsed"
        :expandable="!collapsed && hasSubTabs('/logs')"
        :expanded="!collapsed && isExpanded('/logs')"
        @navigate="closeMobile"
      />
      <transition name="sb-subtabs">
        <div v-if="!collapsed && isExpanded('/logs')" class="sb-subtabs">
          <SidebarSubLink
            v-for="sub in getSubs('/logs')"
            :key="sub.id"
            parent-path="/logs"
            :tab-id="sub.id"
            :label="t(sub.labelKey)"
            :icon="sub.icon"
            :default-tab-id="firstTabId('/logs')"
            @navigate="closeMobile"
          />
        </div>
      </transition>
    </nav>

    <div class="sb-footer">
      <router-link to="/changelog" class="sb-version-link" :title="$t('changelog.title')">
        <span class="sb-version">
          <Tag v-if="!collapsed" :size="11" :stroke-width="2" class="sb-version-icon" />
          v{{ appVersion }}
        </span>
        <span v-if="hasNewChangelog" class="sb-version-dot" />
      </router-link>
      <router-link
        v-if="!collapsed"
        to="/about"
        class="sb-about-link"
        :title="$t('attribution.about.title')"
      >
        {{ $t('attribution.about.title') }}
      </router-link>
    </div>
  </aside>

  <Teleport to="body">
    <transition name="sb-overlay">
      <div v-if="mobileOpen" class="sb-overlay" @click="closeMobile" />
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import SidebarLink from './SidebarLink.vue'
import SidebarSubLink from './SidebarSubLink.vue'
import SidebarSection from './SidebarSection.vue'
import { useSidebarCounters } from '@/composables/useSidebarCounters'
import { fetchApiResponse, useApi } from '@/composables/useApi'
import { useMobile } from '@/composables/useMobile'
import { ChevronLeft, MessageSquare, Search, Tag } from 'lucide-vue-next'
import { SIDEBAR_SUB_TABS } from '@/constants/sidebarSubTabs'
import { SIDEBAR_MODULES } from '@/constants/sidebarModules'

import '@/assets/styles/app-sidebar.css'

const { t } = useI18n()
const { counters } = useSidebarCounters()
const router = useRouter()
const route = useRoute()
const { apiPost } = useApi()
const { isMobile } = useMobile()

const moduleEntries = computed(() =>
  SIDEBAR_MODULES.filter(m => !m.desktopOnly || !isMobile.value),
)

function hasSubTabs(path) {
  return Array.isArray(SIDEBAR_SUB_TABS[path]) && SIDEBAR_SUB_TABS[path].length > 0
}

function getSubs(path) {
  return SIDEBAR_SUB_TABS[path] || []
}

function firstTabId(path) {
  const list = SIDEBAR_SUB_TABS[path]
  return list && list[0] ? list[0].id : null
}

function isExpanded(path) {
  if (!hasSubTabs(path)) return false
  if (path === '/admin/portal') return route.path === path
  return route.path === path || route.path.startsWith(path + '/')
}

async function enterRequestsModule() {
  try {
    await apiPost('/api/portal/admin/requests/enter')
  } catch {
    // Non-fatal: navigation will land on the portal login if provisioning failed.
  }
  closeMobile()
  router.push('/portal')
}

const appVersion = ref('...')
const hasNewChangelog = ref(false)

defineProps({
  collapsed: Boolean,
  mobileOpen: Boolean,
})

const emit = defineEmits(['toggle', 'closeMobile', 'openSearch'])

function closeMobile() {
  emit('closeMobile')
}

onMounted(async () => {
  try {
    const res = await fetchApiResponse('/api/changelog/check', { redirectOn401: false })
    if (res.ok) {
      const data = await res.json()
      appVersion.value = data.current_version || '0.0.0'
      hasNewChangelog.value = !!data.has_new
    }
  } catch {
    // Fallback si l'API n'est pas encore ready
    try {
      const res = await fetchApiResponse('/api/changelog/current', {
        retryOn401: false,
        redirectOn401: false,
      })
      if (res.ok) {
        const data = await res.json()
        appVersion.value = data.version || '0.0.0'
      }
    } catch {
      /* silent: version display is cosmetic */
    }
  }
})
</script>
