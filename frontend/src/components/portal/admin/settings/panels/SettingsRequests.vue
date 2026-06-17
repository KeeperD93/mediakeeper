<template>
  <SettingsSection
    :icon="Inbox"
    :title="$t('portal.admin.settings.cat.requests')"
    :description="$t('portal.admin.settings.cat.requestsDesc')"
  >
    <SettingRow
      :label="$t('portal.admin.settings.anonymizeRequests.title')"
      :description="$t('portal.admin.settings.anonymizeRequests.desc')"
    >
      <MkToggle
        :model-value="draft['anonymize_requests']"
        :aria-label="$t('portal.admin.settings.anonymizeRequests.title')"
        @update:model-value="v => (draft['anonymize_requests'] = v)"
      />
    </SettingRow>

    <SettingRow
      :label="$t('portal.admin.settings.allowAdultRequests.title')"
      :description="$t('portal.admin.settings.allowAdultRequests.desc')"
    >
      <MkToggle
        :model-value="draft['allow_adult_requests']"
        :aria-label="$t('portal.admin.settings.allowAdultRequests.title')"
        @update:model-value="v => (draft['allow_adult_requests'] = v)"
      />
    </SettingRow>

    <SettingRow
      :label="$t('portal.admin.settings.requestsCleanup.title')"
      :description="$t('portal.admin.settings.requestsCleanup.desc')"
      :control-id="cleanupId"
    >
      <input
        :id="cleanupId"
        v-model.number="draft['requests.auto_cleanup_days']"
        class="set-input"
        type="number"
        min="0"
        max="365"
      />
    </SettingRow>
  </SettingsSection>
</template>

<script setup>
import { inject, useId } from 'vue'
import { Inbox } from 'lucide-vue-next'
import MkToggle from '@/components/common/MkToggle.vue'
import SettingsSection from '../SettingsSection.vue'
import SettingRow from '../SettingRow.vue'

const { draft } = inject('settingsDraft')
const cleanupId = useId()
</script>
