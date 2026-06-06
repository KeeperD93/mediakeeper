<template>
  <div
    class="mm-overlay"
    :class="{ show: showAdvancedModal }"
    @click.self="showAdvancedModal = false"
  >
    <div
      ref="advPanelRef"
      class="mm-config-modal mm-config-modal-760"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      tabindex="-1"
    >
      <div class="mm-config-sidebar">
        <div :id="titleId" class="mm-config-sidebar-title">
          <Wrench :size="14" />
          {{ $t('mediaManager.advancedTools') }}
        </div>
        <button
          v-for="tab in ADVANCED_TABS"
          :key="tab.id"
          class="mm-config-tab"
          :class="{ active: advancedTab === tab.id }"
          @click="advancedTab = tab.id"
        >
          <component :is="tab.icon" :size="13" />
          {{ tab.label }}
        </button>
      </div>
      <div class="mm-config-content">
        <div class="mm-config-header">
          <span>{{ advancedTabLabel }}</span>
          <button
            class="mm-btn-sm mm-close-btn"
            type="button"
            :aria-label="$t('common.close')"
            @click="showAdvancedModal = false"
          >
            <X :size="14" />
          </button>
        </div>

        <!-- Profils -->
        <div v-if="advancedTab === 'profiles'" class="mm-config-body">
          <p class="mm-desc">{{ $t('mediaManager.advProfilesDesc') }}</p>
          <div class="mm-adv-profiles">
            <div
              v-for="p in getAllProfiles()"
              :key="p.id"
              class="mm-adv-profile-card"
              :class="{ builtin: p.builtin }"
            >
              <div class="mm-adv-profile-name">{{ p.name }}</div>
              <div class="mm-adv-profile-fmt">
                <span class="mm-rf-tag mm-rf-tag-sm">{{ $t('common.film') }}</span>
                {{ p.config.movie }}
                <br />
                <span class="mm-rf-tag mm-rf-tag-sm">{{ $t('common.series') }}</span>
                {{ p.config.tv }}
              </div>
              <div class="mm-adv-profile-actions">
                <button class="mm-btn-sm mm-btn-accent" @click="applyProfileLocal(p)">
                  {{ $t('common.apply') }}
                </button>
                <button v-if="!p.builtin" class="mm-btn-sm mm-btn-del" @click="deleteProfile(p.id)">
                  ✕
                </button>
              </div>
            </div>
          </div>
          <hr class="mm-divider" />
          <div class="mm-label">{{ $t('mediaManager.saveCurrentProfileAdv') }}</div>
          <div class="mm-save-row">
            <input
              v-model="newProfileName"
              class="mm-folder-input mm-input-flat mm-input-flex"
              :placeholder="$t('mediaManager.profileNamePlaceholder')"
              @keydown.enter="saveCurrentAsProfile"
            />
            <button class="mm-btn-sm mm-btn-success" @click="saveCurrentAsProfile">
              {{ $t('mediaManager.saveBtnLabel') }}
            </button>
          </div>
        </div>

        <MMRulesPanel v-if="advancedTab === 'rules'" />
        <MMCsvPanel v-if="advancedTab === 'csv'" use-count-suffix />
        <MMDupesPanel v-if="advancedTab === 'dupes'" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaManager } from '@/composables/useMediaManager'
import { useMMConfigPanels } from '@/composables/useMMConfigPanels'
import { useFocusTrap } from '@/composables/useFocusTrap'
import MMRulesPanel from './MMRulesPanel.vue'
import MMCsvPanel from './MMCsvPanel.vue'
import MMDupesPanel from './MMDupesPanel.vue'
import { Code2, Copy, FileDown, Folder, Wrench, X } from 'lucide-vue-next'

const { t } = useI18n()

const { showAdvancedModal, advancedTab, getAllProfiles, deleteProfile } = useMediaManager()
const { newProfileName, applyProfileLocal, saveCurrentAsProfile } = useMMConfigPanels()

const advPanelRef = ref(null)
const titleId = useId()
useFocusTrap({
  active: computed(() => showAdvancedModal.value),
  containerRef: advPanelRef,
  onEscape: () => (showAdvancedModal.value = false),
})

const ADVANCED_TABS = [
  { id: 'profiles', label: t('mediaManager.profilesTab'), icon: Folder },
  { id: 'rules', label: t('mediaManager.customRulesTab'), icon: Code2 },
  { id: 'csv', label: t('mediaManager.csvTab'), icon: FileDown },
  { id: 'dupes', label: t('mediaManager.crossCatDupesTab'), icon: Copy },
]
const advancedTabLabel = computed(
  () => ADVANCED_TABS.find(t => t.id === advancedTab.value)?.label || '',
)
</script>

<style scoped>
/* Modal width */
.mm-config-modal-760 {
  width: 760px;
}
/* Close button (header ×) */
.mm-close-btn {
  padding: 3px 8px;
}
/* Section description */
.mm-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}
/* Smaller version of the .mm-rf-tag pill (used inside the profile card) */
.mm-rf-tag-sm {
  font-size: 0.6rem;
}
/* Delete (red) button inside the profile card */
.mm-btn-del {
  color: var(--mm-red);
}
/* Divider between profiles list and "save profile" form */
.mm-divider {
  border-color: var(--border);
  margin: 0.8rem 0;
}
/* Save-profile row (input + button) */
.mm-save-row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.4rem;
}
.mm-input-flat {
  margin-top: 0;
}
.mm-input-flex {
  flex: 1;
}
</style>
