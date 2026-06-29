<template>
  <div class="cinema-params mk-page-root">
    <div class="params-inner">
      <div class="params-content">
        <KeepAlive>
          <component :is="currentTabComponent" />
        </KeepAlive>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { useTabSync } from '@/composables/useTabSync'
import { SIDEBAR_SUB_TABS } from '@/constants/sidebarSubTabs'
const ParamsGeneralTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsGeneralTab.vue'),
)
const ParamsAppearanceTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsAppearanceTab.vue'),
)
const ParamsConfigTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsConfigTab.vue'),
)
const ParamsSchedulerTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsSchedulerTab.vue'),
)
const ParamsNetworkTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsNetworkTab.vue'),
)
const ParamsBackupTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsBackupTab.vue'),
)
const ParamsSecurityTab = defineAsyncComponent(
  () => import('@/components/settings/ParamsSecurityTab.vue'),
)
import '@/assets/styles/params-view.css'

const TAB_IDS = SIDEBAR_SUB_TABS['/settings'].map(t => t.id)
const activeTab = useTabSync(TAB_IDS, TAB_IDS[0])

const TAB_COMPONENTS = {
  general: ParamsGeneralTab,
  appearance: ParamsAppearanceTab,
  config: ParamsConfigTab,
  scheduler: ParamsSchedulerTab,
  network: ParamsNetworkTab,
  backup: ParamsBackupTab,
  security: ParamsSecurityTab,
}
const currentTabComponent = computed(() => TAB_COMPONENTS[activeTab.value] || ParamsGeneralTab)
</script>
