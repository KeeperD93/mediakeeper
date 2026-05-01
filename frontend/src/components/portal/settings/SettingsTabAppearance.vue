<template>
  <div class="pt-settings-card">
    <h3 class="pt-settings-section-title">{{ $t('portal.settings.appearance.titleSection') }}</h3>
    <p class="pt-settings-section-sub">{{ $t('portal.settings.appearance.titleSubtitle') }}</p>

    <div class="pt-settings-chips">
      <button
        type="button"
        class="pt-settings-chip"
        :class="{ 'pt-settings-chip--on': !form.selected_title }"
        @click="updateField('selected_title', null)"
      >
        {{ $t('portal.settings.appearance.titleNone') }}
      </button>
      <button
        v-for="key in availableTitles"
        :key="key"
        type="button"
        class="pt-settings-chip"
        :class="{ 'pt-settings-chip--on': form.selected_title === key }"
        @click="updateField('selected_title', key)"
      >
        {{ $t(key) }}
      </button>
    </div>

    <button
      v-if="titleCatalogue.length"
      type="button"
      class="pt-settings-btn"
      @click="howtoOpen = !howtoOpen"
    >
      {{ howtoOpen
          ? $t('portal.settings.appearance.hideHowToUnlock')
          : $t('portal.settings.appearance.showHowToUnlock') }}
    </button>

    <div v-if="howtoOpen" class="pt-settings-howto">
      <ul class="pt-settings-howto-list">
        <li
          v-for="item in titleCatalogue"
          :key="item.title_key"
          class="pt-settings-howto-row"
          :class="{ 'is-unlocked': item.unlocked }"
        >
          <span class="pt-settings-howto-name">
            {{ item.unlocked ? '✓' : '🔒' }} {{ $t(item.title_key) }}
          </span>
          <span>
            ←
            <template v-if="item.secret">
              {{ $t('portal.settings.appearance.titleSecretHint') }}
            </template>
            <template v-else>
              {{ $t(item.achievement_name_key) }}
              <em> · {{ $t(item.achievement_description_key) }}</em>
            </template>
          </span>
        </li>
      </ul>
    </div>

    <hr class="pt-settings-divider" />

    <h3 class="pt-settings-section-title">{{ $t('portal.settings.appearance.fxSection') }}</h3>
    <p class="pt-settings-section-sub">{{ $t('portal.settings.appearance.fxSubtitle') }}</p>

    <div class="pt-settings-chips">
      <button
        type="button"
        class="pt-settings-chip"
        :class="{ 'pt-settings-chip--on': !form.avatar_effect }"
        @click="updateField('avatar_effect', null)"
      >
        {{ $t('portal.settings.appearance.fxNone') }}
      </button>
      <button
        v-for="fx in availableAvatarEffects"
        :key="fx"
        type="button"
        class="pt-settings-chip"
        :class="{ 'pt-settings-chip--on': form.avatar_effect === fx }"
        @click="updateField('avatar_effect', fx)"
      >
        {{ $t(`portal.profile.avatarEffects.${fx}`) }}
      </button>
    </div>

    <p v-if="!availableAvatarEffects.length" class="pt-settings-hint">
      {{ $t('portal.settings.appearance.fxLockedHint') }}
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  form: { type: Object, required: true },
  availableTitles: { type: Array, default: () => [] },
  availableAvatarEffects: { type: Array, default: () => [] },
  titleCatalogue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update-field'])

const howtoOpen = ref(false)

function updateField(key, value) {
  emit('update-field', key, value)
}
</script>

<style scoped>
.pt-settings-divider {
  border: none;
  border-top: 1px solid var(--portal-border-default);
  margin: 0.5rem 0;
}
</style>
