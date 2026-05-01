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
const ParamsGeneralTab = defineAsyncComponent(() => import('@/components/settings/ParamsGeneralTab.vue'))
const ParamsAppearanceTab = defineAsyncComponent(() => import('@/components/settings/ParamsAppearanceTab.vue'))
const ParamsConfigTab = defineAsyncComponent(() => import('@/components/settings/ParamsConfigTab.vue'))
const ParamsSchedulerTab = defineAsyncComponent(() => import('@/components/settings/ParamsSchedulerTab.vue'))
const ParamsTestTab = defineAsyncComponent(() => import('@/components/settings/ParamsTestTab.vue'))
const ParamsBackupTab = defineAsyncComponent(() => import('@/components/settings/ParamsBackupTab.vue'))
const ParamsSecurityTab = defineAsyncComponent(() => import('@/components/settings/ParamsSecurityTab.vue'))
import '@/assets/styles/params-view.css'

const TAB_IDS = ['general', 'appearance', 'config', 'scheduler', 'backup', 'test', 'security']
const activeTab = useTabSync(TAB_IDS, 'general')

const TAB_COMPONENTS = {
  general: ParamsGeneralTab,
  appearance: ParamsAppearanceTab,
  config: ParamsConfigTab,
  scheduler: ParamsSchedulerTab,
  test: ParamsTestTab,
  backup: ParamsBackupTab,
  security: ParamsSecurityTab,
}
const currentTabComponent = computed(() => TAB_COMPONENTS[activeTab.value] || ParamsGeneralTab)
</script>
