<template>
  <div class="pt-admin">
    <div class="pt-admin-content">
      <AdminBlacklist v-if="activeTab === 'blacklist'" />
      <AdminNews v-else-if="activeTab === 'news'" />
      <AdminFeatured v-else-if="activeTab === 'featured'" />
      <AdminXpEvents v-else-if="activeTab === 'xpEvents'" />
      <AdminSettings v-else-if="activeTab === 'settings'" />
      <AdminDebug v-else-if="activeTab === 'debug'" />
    </div>
  </div>
</template>

<script setup>
import { useTabSync } from '@/composables/useTabSync'
import { SIDEBAR_SUB_TABS } from '@/constants/sidebarSubTabs'
import AdminBlacklist from '@/components/portal/admin/AdminBlacklist.vue'
import AdminNews from '@/components/portal/admin/AdminNews.vue'
import AdminFeatured from '@/components/portal/admin/AdminFeatured.vue'
import AdminXpEvents from '@/components/portal/admin/AdminXpEvents.vue'
import AdminSettings from '@/components/portal/admin/AdminSettings.vue'
import AdminDebug from '@/components/portal/admin/AdminDebug.vue'

const TAB_IDS = SIDEBAR_SUB_TABS['/admin/portal'].map(t => t.id)
const activeTab = useTabSync(TAB_IDS, TAB_IDS[0])
</script>

<style scoped>
.pt-admin {
  padding: 1.5rem;
}
</style>
