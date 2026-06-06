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

const props = defineProps({
  form: { type: Object, required: true },
})
const emit = defineEmits(['update-field'])

const GENRE_PICKER = [
  { label: 'action', ids: [28, 10759], emoji: '💥', color: '#ef4444' },
  { label: 'aventure', ids: [12], emoji: '⚔️', color: '#f97316' },
  { label: 'animation', ids: [16], emoji: '✏️', color: '#a78bfa' },
  { label: 'comedie', ids: [35], emoji: '😂', color: '#fbbf24' },
  { label: 'crime', ids: [80], emoji: '🔫', color: '#dc2626' },
  { label: 'documentaire', ids: [99], emoji: '🎥', color: '#22c55e' },
  { label: 'drame', ids: [18], emoji: '🎭', color: '#3b82f6' },
  { label: 'familial', ids: [10751], emoji: '👨‍👩‍👧', color: '#22c55e' },
  { label: 'fantastique', ids: [14], emoji: '🧙', color: '#8b5cf6' },
  { label: 'guerre', ids: [10752, 10768], emoji: '⚔️', color: '#7c2d12' },
  { label: 'histoire', ids: [36], emoji: '🏛️', color: '#b45309' },
  { label: 'horreur', ids: [27], emoji: '😱', color: '#991b1b' },
  { label: 'mystere', ids: [9648], emoji: '🔍', color: '#6366f1' },
  { label: 'musique', ids: [10402], emoji: '🎵', color: '#c084fc' },
  { label: 'romance', ids: [10749], emoji: '❤️', color: '#ec4899' },
  { label: 'scienceFiction', ids: [878, 10765], emoji: '🚀', color: '#38bdf8' },
  { label: 'thriller', ids: [53], emoji: '😰', color: '#64748b' },
  { label: 'western', ids: [37], emoji: '🤠', color: '#a16207' },
]

function isGenreSelected(g) {
  return g.ids.some(id => props.form.favorite_genres.includes(id))
}
function toggleGenre(g) {
  if (isGenreSelected(g)) {
    updateField(
      'favorite_genres',
      props.form.favorite_genres.filter(id => !g.ids.includes(id)),
    )
  } else {
    updateField('favorite_genres', [...props.form.favorite_genres, ...g.ids])
  }
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
