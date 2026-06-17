<template>
  <SettingsSection
    :icon="Languages"
    :title="$t('portal.admin.settings.cat.language')"
    :description="$t('portal.admin.settings.cat.languageDesc')"
  >
    <SettingRow
      :label="$t('portal.admin.settings.defaultLanguage.title')"
      :description="$t('portal.admin.settings.defaultLanguage.desc')"
      :control-id="langId"
    >
      <select :id="langId" v-model="draft['default_language']" class="set-select">
        <option value="">{{ $t('portal.admin.settings.defaultLanguage.auto') }}</option>
        <option v-for="loc in AVAILABLE_LOCALES" :key="loc.code" :value="loc.code">
          {{ loc.label }}
        </option>
      </select>
    </SettingRow>
  </SettingsSection>
</template>

<script setup>
import { inject, useId } from 'vue'
import { Languages } from 'lucide-vue-next'
import { AVAILABLE_LOCALES } from '@/i18n'
import SettingsSection from '../SettingsSection.vue'
import SettingRow from '../SettingRow.vue'

const { draft } = inject('settingsDraft')
const langId = useId()
</script>
