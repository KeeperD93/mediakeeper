<template>
  <div class="pt-admin">
    <div class="pt-admin-header">
      <h2>{{ $t('portal.admin.title') }}</h2>
    </div>

    <div v-if="stats" class="pt-admin-stats">
      <div class="pt-stat-card">
        <span class="pt-stat-val">{{ stats.total_users }}</span>
        <span class="pt-stat-label">{{ $t('portal.admin.totalUsers') }}</span>
      </div>
      <div class="pt-stat-card">
        <span class="pt-stat-val">{{ stats.pending_requests }}</span>
        <span class="pt-stat-label">{{ $t('portal.admin.pendingRequests') }}</span>
      </div>
      <div class="pt-stat-card">
        <span class="pt-stat-val">{{ stats.open_tickets }}</span>
        <span class="pt-stat-label">{{ $t('portal.admin.openTickets') }}</span>
      </div>
    </div>

    <div class="pt-admin-content">
      <AdminBlacklist v-if="activeTab === 'blacklist'" />
      <AdminTickets v-else-if="activeTab === 'tickets'" />
      <AdminNews v-else-if="activeTab === 'news'" />
      <AdminFeatured v-else-if="activeTab === 'featured'" />
      <AdminXpEvents v-else-if="activeTab === 'xpEvents'" />
      <AdminLists v-else-if="activeTab === 'lists'" />
      <AdminSettings v-else-if="activeTab === 'settings'" />
      <AdminDebug v-else-if="activeTab === 'debug'" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { usePortalAdmin } from '@/composables/portal/usePortalAdmin'
import { useTabSync } from '@/composables/useTabSync'
import AdminBlacklist from '@/components/portal/admin/AdminBlacklist.vue'
import AdminTickets from '@/components/portal/admin/AdminTickets.vue'
import AdminNews from '@/components/portal/admin/AdminNews.vue'
import AdminFeatured from '@/components/portal/admin/AdminFeatured.vue'
import AdminXpEvents from '@/components/portal/admin/AdminXpEvents.vue'
import AdminLists from '@/components/portal/admin/AdminLists.vue'
import AdminSettings from '@/components/portal/admin/AdminSettings.vue'
import AdminDebug from '@/components/portal/admin/AdminDebug.vue'

const { stats, fetchStats } = usePortalAdmin()
const TAB_IDS = ['blacklist', 'tickets', 'news', 'featured', 'xpEvents', 'lists', 'settings', 'debug']
const activeTab = useTabSync(TAB_IDS, 'blacklist')

onMounted(() => fetchStats())
</script>

<style scoped>
.pt-admin { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
.pt-admin-header { margin-bottom: 1.25rem; }
.pt-admin-header h2 { font-size: var(--portal-text-xl); font-weight: var(--portal-font-bold); color: var(--text-primary); }
.pt-admin-stats { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.5rem; }
@media (min-width: 640px) {
  .pt-admin-stats { flex-direction: row; }
}
.pt-stat-card {
  flex: 1;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  text-align: center;
}
.pt-stat-val { display: block; font-size: var(--portal-text-2xl); font-weight: var(--portal-font-extrabold); color: var(--accent); }
.pt-stat-label { font-size: var(--portal-text-xs); color: var(--text-muted); }
</style>
