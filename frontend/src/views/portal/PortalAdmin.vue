<template>
  <div class="pt-admin">
    <div class="pt-admin-content">
      <AdminBlacklist v-if="activeTab === 'blacklist'" />
      <AdminTickets v-else-if="activeTab === 'tickets'" />
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
import AdminBlacklist from '@/components/portal/admin/AdminBlacklist.vue'
import AdminTickets from '@/components/portal/admin/AdminTickets.vue'
import AdminNews from '@/components/portal/admin/AdminNews.vue'
import AdminFeatured from '@/components/portal/admin/AdminFeatured.vue'
import AdminXpEvents from '@/components/portal/admin/AdminXpEvents.vue'
import AdminSettings from '@/components/portal/admin/AdminSettings.vue'
import AdminDebug from '@/components/portal/admin/AdminDebug.vue'

const TAB_IDS = [
  'blacklist',
  'tickets',
  'news',
  'featured',
  'xpEvents',
  'settings',
  'debug',
]
const activeTab = useTabSync(TAB_IDS, 'blacklist')
</script>

<style scoped>
.pt-admin {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem;
}
</style>
