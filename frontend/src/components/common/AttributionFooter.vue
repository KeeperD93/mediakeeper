<template>
  <footer class="mk-attribution" role="contentinfo">
    <a
      class="mk-attribution-logo-link"
      :href="tmdbUrl"
      target="_blank"
      rel="noopener noreferrer"
      :aria-label="t('common.attribution.logoAlt')"
    >
      <img
        class="mk-attribution-logo"
        :src="tmdbLogoUrl"
        :alt="t('common.attribution.logoAlt')"
        width="48"
        height="auto"
        loading="lazy"
        decoding="async"
      />
    </a>
    <p class="mk-attribution-text">
      {{ t('common.attribution.text') }}
      <span class="mk-attribution-sep" aria-hidden="true">·</span>
      <router-link :to="{ name: 'portal-credits' }" class="mk-attribution-credits">
        {{ t('attribution.footer.fullCredits') }}
      </router-link>
    </p>
  </footer>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const tmdbUrl = 'https://www.themoviedb.org'
const tmdbLogoUrl = '/assets/icons/tmdb.svg'
</script>

<style scoped>
.mk-attribution {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px 12px;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
  text-align: center;
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-muted, var(--text-secondary));
  background: transparent;
}

.mk-attribution-logo-link {
  display: inline-flex;
  align-items: center;
  border-radius: 2px;
}

.mk-attribution-logo-link:focus-visible {
  outline: 2px solid var(--accent-500, currentColor);
  outline-offset: 2px;
}

.mk-attribution-logo {
  display: block;
  height: 16px;
  width: auto;
  opacity: 0.85;
  transition: opacity 150ms ease;
}

@media (hover: hover) {
  .mk-attribution-logo-link:hover .mk-attribution-logo {
    opacity: 1;
  }
}

.mk-attribution-text {
  margin: 0;
  max-width: 60ch;
}

.mk-attribution-sep {
  margin: 0 4px;
  opacity: 0.6;
}

.mk-attribution-credits {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.mk-attribution-credits:hover,
.mk-attribution-credits:focus-visible {
  color: var(--text-primary);
}
</style>
