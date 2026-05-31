<template>
  <div class="mm-config-body">
    <p class="mm-desc">{{ $t('mediaManager.profilesDesc') }}</p>
    <div class="mm-label mm-label-gap">{{ $t('mediaManager.availableProfiles') }}</div>
    <div class="mm-profile-list">
      <div v-for="profile in profiles" :key="profile.id" class="mm-profile-row">
        <div class="mm-profile-info">
          <span class="mm-profile-name">{{ profile.name }}</span>
          <span class="mm-profile-meta">{{ profile.config.movie }} · {{ profile.config.tv }}</span>
        </div>
        <div class="mm-profile-actions">
          <button
            class="mm-btn-sm mm-btn-accent mm-profile-use-btn"
            @click="$emit('apply-profile', profile)"
          >
            {{ $t('common.use') }}
          </button>
          <button
            v-if="!profile.builtin"
            class="mm-btn-sm mm-profile-del-btn"
            @click="$emit('delete-profile', profile.id)"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
    <div class="mm-label mm-label-gap">{{ $t('mediaManager.saveCurrentProfile') }}</div>
    <div class="mm-field-row">
      <input
        :value="newProfileName"
        class="mm-folder-input mm-input-flat mm-input-flex"
        :placeholder="$t('mediaManager.profileNamePlaceholder')"
        @input="$emit('update:newProfileName', $event.target.value)"
        @keydown.enter="$emit('save-profile')"
      />
      <button
        class="mm-btn-sm mm-btn-success"
        :class="{ 'mm-btn-saved': saved }"
        @click="$emit('save-profile')"
      >
        <Check />
        {{ saved ? $t('mediaManager.savedBtnProfile') : $t('mediaManager.saveBtnProfile') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { Check } from 'lucide-vue-next'

defineProps({
  profiles: { type: Array, required: true },
  newProfileName: { type: String, default: '' },
  saved: { type: Boolean, default: false },
})
defineEmits(['apply-profile', 'delete-profile', 'save-profile', 'update:newProfileName'])
</script>

<style scoped>
.mm-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}
.mm-label-gap {
  margin-bottom: 0.4rem;
}
.mm-input-flat {
  margin-top: 0;
}
.mm-input-flex {
  flex: 1;
}
.mm-field-row {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}
.mm-profile-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.9rem;
}
.mm-profile-actions {
  display: flex;
  gap: 0.3rem;
  flex-shrink: 0;
}
.mm-profile-use-btn {
  padding: 2px 8px;
  font-size: var(--text-3xs);
}
.mm-profile-del-btn {
  padding: 2px 6px;
  color: var(--mm-red);
  font-size: var(--text-2xs);
}
</style>
