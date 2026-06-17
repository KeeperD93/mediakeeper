<template>
  <SettingsSection
    :icon="Clapperboard"
    :title="$t('portal.admin.settings.cat.events')"
    :description="$t('portal.admin.settings.cat.eventsDesc')"
  >
    <SettingRow
      :label="$t('portal.admin.settings.eventCapacityMin.title')"
      :description="$t('portal.admin.settings.eventCapacityMin.desc')"
      :control-id="minId"
    >
      <select :id="minId" v-model.number="draft['events.max_participants_min']" class="set-select">
        <option v-for="v in CAPACITY_OPTIONS" :key="`min-${v}`" :value="v">{{ v }}</option>
      </select>
    </SettingRow>

    <SettingRow
      :label="$t('portal.admin.settings.eventCapacityMax.title')"
      :description="$t('portal.admin.settings.eventCapacityMax.desc')"
      :control-id="maxId"
    >
      <select :id="maxId" v-model.number="draft['events.max_participants_max']" class="set-select">
        <option v-for="v in CAPACITY_OPTIONS" :key="`max-${v}`" :value="v">{{ v }}</option>
      </select>
    </SettingRow>
  </SettingsSection>
</template>

<script setup>
import { inject, useId } from 'vue'
import { Clapperboard } from 'lucide-vue-next'
import SettingsSection from '../SettingsSection.vue'
import SettingRow from '../SettingRow.vue'

// Step-5 options matching the backend PORTAL_EVENT_CAPACITY_STEP; the service
// layer snaps/re-orders if min > max.
const CAPACITY_OPTIONS = [5, 10, 15, 20]

const { draft } = inject('settingsDraft')
const minId = useId()
const maxId = useId()
</script>
