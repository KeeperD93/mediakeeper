<template>
  <SettingsSection
    :icon="Home"
    :title="$t('portal.admin.settings.cat.home')"
    :description="$t('portal.admin.settings.cat.homeDesc')"
  >
    <SettingRow
      :label="$t('portal.admin.settings.heroTrendCount.title')"
      :description="$t('portal.admin.settings.heroTrendCount.desc')"
      :control-id="heroId"
    >
      <input
        :id="heroId"
        v-model.number="draft['hero_trend_count']"
        class="set-input"
        type="number"
        min="0"
        max="20"
      />
    </SettingRow>
  </SettingsSection>
</template>

<script setup>
import { inject, useId } from 'vue'
import { Home } from 'lucide-vue-next'
import SettingsSection from '../SettingsSection.vue'
import SettingRow from '../SettingRow.vue'

const { draft } = inject('settingsDraft')
const heroId = useId()
</script>
