<template>
  <div class="set-page">
    <SettingsRequests class="set-block" />
    <AdminAutoQuotaSetting class="set-block" />
    <SettingsHome class="set-block" />
    <SettingsEvents class="set-block" />
    <SettingsChat class="set-block" />
    <SettingsLanguage class="set-block" />
    <AdminDonationSetting class="set-block" />
    <SettingsMaintenance class="set-block" />
    <GdprSection class="set-block" />

    <SettingsSaveBar
      :dirty="dirty"
      :saving="saving"
      :invalid="invalid"
      @save="save"
      @reset="reset"
    />
  </div>
</template>

<script setup>
import { onMounted, provide } from 'vue'
import { useSettingsDraft } from '@/composables/portal/useSettingsDraft'
import SettingsSaveBar from './settings/SettingsSaveBar.vue'
import SettingsRequests from './settings/panels/SettingsRequests.vue'
import SettingsHome from './settings/panels/SettingsHome.vue'
import SettingsEvents from './settings/panels/SettingsEvents.vue'
import SettingsChat from './settings/panels/SettingsChat.vue'
import SettingsLanguage from './settings/panels/SettingsLanguage.vue'
import SettingsMaintenance from './settings/panels/SettingsMaintenance.vue'
// Complex categories still render their existing self-contained components for
// now (own title + Save button); they migrate onto the shared iconified
// section + global draft in the next phase.
import AdminAutoQuotaSetting from './AdminAutoQuotaSetting.vue'
import AdminDonationSetting from './AdminDonationSetting.vue'
import GdprSection from './GdprSection.vue'
import '@/assets/styles/portal/admin-settings.css'

const draftApi = useSettingsDraft()
const { dirty, saving, invalid, load, save, reset } = draftApi
provide('settingsDraft', draftApi)

onMounted(load)
</script>

<style scoped>
.set-page {
  display: flex;
  flex-direction: column;
  max-width: 760px;
}
.set-block + .set-block {
  margin-top: 1.75rem;
  padding-top: 1.75rem;
  border-top: 1px solid var(--border);
}
</style>
