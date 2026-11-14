<template>
  <div class="pt-settings-card">
    <h3 class="pt-settings-section-title">
      {{ $t('portal.settings.preferences.languageSection') }}
    </h3>
    <p class="pt-settings-section-sub">{{ $t('portal.settings.preferences.languageHint') }}</p>

    <div class="pt-settings-chips">
      <button
        type="button"
        class="pt-settings-chip"
        :class="{ 'pt-settings-chip--on': !form.language }"
        @click="updateField('language', null)"
      >
        <span>🌐</span>
        <span>{{ $t('portal.settings.preferences.languageDefault') }}</span>
      </button>
      <button
        v-for="loc in AVAILABLE_LOCALES"
        :key="loc.code"
        type="button"
        class="pt-settings-chip"
        :class="{ 'pt-settings-chip--on': form.language === loc.code }"
        @click="updateField('language', loc.code)"
      >
        <span>{{ loc.flag }}</span>
        <span>{{ loc.label }}</span>
      </button>
    </div>

    <hr class="pt-settings-divider" />

    <h3 class="pt-settings-section-title">{{ $t('portal.settings.preferences.genresSection') }}</h3>
    <p class="pt-settings-section-sub">{{ $t('portal.settings.preferences.genresHint') }}</p>

    <div class="pt-settings-chips">
      <button
        v-for="g in GENRE_PICKER"
        :key="g.label"
        type="button"
        class="pt-settings-chip"
        :class="{ 'pt-settings-chip--on': isGenreSelected(g) }"
        :style="
          isGenreSelected(g)
            ? { borderColor: g.color, background: g.color + '22', color: '#fff' }
            : null
        "
        @click="toggleGenre(g)"
      >
        <span>{{ g.emoji }}</span>
        <span>{{ $t(`portal.genres.${g.label}`) }}</span>
      </button>
    </div>

    <hr class="pt-settings-divider" />

    <h3 class="pt-settings-section-title">{{ $t('portal.settings.preferences.adultSection') }}</h3>

    <label class="pt-settings-toggle">
      <input
        type="checkbox"
        :checked="form.hide_adult"
        @change="updateField('hide_adult', $event.target.checked)"
      />
      <span class="pt-settings-toggle-text">
        <span class="pt-settings-toggle-label">
          {{ $t('portal.settings.preferences.hideAdult') }}
        </span>
        <span class="pt-settings-toggle-hint">
          {{ $t('portal.settings.preferences.hideAdultHint') }}
        </span>
      </span>
    </label>
  </div>
</template>

<script setup>
import { AVAILABLE_LOCALES } from '@/i18n'
import { GENRE_PICKER, isGenrePicked, toggleGenrePick } from '@/constants/portalGenres'

const props = defineProps({
  form: { type: Object, required: true },
})
const emit = defineEmits(['update-field'])

function isGenreSelected(g) {
  return isGenrePicked(g, props.form.favorite_genres)
}
function toggleGenre(g) {
  updateField('favorite_genres', toggleGenrePick(g, props.form.favorite_genres))
}

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
