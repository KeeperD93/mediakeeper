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
  flex-wrap: nowrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 14px calc(8px + env(safe-area-inset-bottom, 0px));
  text-align: center;
  font-size: 12px;
  line-height: 1.3;
  color: var(--text-secondary);
  background: transparent;
  min-width: 0;
}

.mk-attribution-logo-link {
  display: inline-flex;
  align-items: center;
  border-radius: 2px;
  flex-shrink: 0;
}

.mk-attribution-logo-link:focus-visible {
  outline: 2px solid var(--accent-500);
  outline-offset: 2px;
}

.mk-attribution-logo {
  display: block;
  height: 13px;
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
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mk-attribution-sep {
  margin: 0 6px;
  opacity: 0.6;
  display: inline-block;
  flex-shrink: 0;
}

.mk-attribution-credits {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
  padding: 8px 2px;
  display: inline-block;
}

.mk-attribution-credits:hover,
.mk-attribution-credits:focus-visible {
  color: var(--text-primary);
}
</style>
