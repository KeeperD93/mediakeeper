<template>
  <nav class="pt-bottom-nav" :aria-label="$t('portal.nav.bottomNav')">
    <div class="pt-bottom-nav-inner">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="pt-bottom-tab"
        :class="{ 'pt-bottom-tab--active': isTabActive(tab.name) }"
        type="button"
        :aria-label="$t(tab.label)"
        :aria-current="isTabActive(tab.name) ? 'page' : undefined"
        @click="$emit('navigate', tab.name)"
      >
        <span class="pt-bottom-tab-icon">
          <component :is="tab.icon" :size="22" :stroke-width="2" />
        </span>
        <span class="pt-bottom-tab-label">{{ $t(tab.label) }}</span>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { Home, User, Compass, LifeBuoy, Library } from 'lucide-vue-next'
import { PORTAL_TAB } from '@/constants/portal'

import '@/assets/styles/portal/nav-bottom.css'

const props = defineProps({
  activeTab: { type: String, default: '' },
  showRequestsTab: { type: Boolean, default: true },
})

defineEmits(['navigate'])

const tabs = computed(() => {
  const base = [
    { name: PORTAL_TAB.HOME, label: 'portal.tabs.home', icon: Home },
    { name: PORTAL_TAB.ME, label: 'portal.tabs.profile', icon: User },
    { name: PORTAL_TAB.LISTS, label: 'portal.lists.navLabel', icon: Library },
  ]
  if (props.showRequestsTab) {
    base.push({ name: PORTAL_TAB.REQUESTS, label: 'portal.tabs.discover', icon: Compass })
  }
  base.push({ name: PORTAL_TAB.TICKETS, label: 'portal.tabs.problems', icon: LifeBuoy })
  return base
})

function isTabActive(name) {
  if (name === PORTAL_TAB.TICKETS) {
    return props.activeTab === PORTAL_TAB.TICKETS || props.activeTab === PORTAL_TAB.TICKET_DETAIL
  }
  return props.activeTab === name
}
</script>
