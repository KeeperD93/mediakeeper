<template>
  <SettingsSection
    :icon="MessageSquare"
    :title="$t('portal.admin.settings.cat.chat')"
    :description="$t('portal.admin.settings.cat.chatDesc')"
  >
    <SettingRow
      :label="$t('portal.admin.settings.chatRetention.title')"
      :description="$t('portal.admin.settings.chatRetention.desc')"
      :control-id="retentionId"
    >
      <input
        :id="retentionId"
        v-model.number="draft['chat.retention_days']"
        class="set-input"
        type="number"
        min="0"
        max="3650"
      />
    </SettingRow>
  </SettingsSection>
</template>

<script setup>
import { inject, useId } from 'vue'
import { MessageSquare } from 'lucide-vue-next'
import SettingsSection from '../SettingsSection.vue'
import SettingRow from '../SettingRow.vue'

const { draft } = inject('settingsDraft')
const retentionId = useId()
</script>
