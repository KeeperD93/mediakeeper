<template>
  <div class="pc-root mk-page-root">
    <div class="pc-inner">
      <header class="pc-header">
        <h1 class="pc-title">{{ t('attribution.credits.title') }}</h1>
        <p class="pc-subtitle">{{ t('attribution.credits.subtitle') }}</p>
      </header>

      <section class="pc-section pc-tmdb" data-test="pc-tmdb">
        <a
          class="pc-tmdb-logo-link"
          :href="links.tmdb"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="t('attribution.tmdb.logoAlt')"
        >
          <img
            class="pc-tmdb-logo"
            :src="tmdbLogoUrl"
            :alt="t('attribution.tmdb.logoAlt')"
            width="120"
            height="auto"
            loading="lazy"
            decoding="async"
            data-test="pc-tmdb-logo"
          />
        </a>
        <p class="pc-legal" data-test="pc-tmdb-legal">{{ tmdbLegalText }}</p>
      </section>

      <section class="pc-section" data-test="pc-opensubtitles">
        <h2 class="pc-h2">OpenSubtitles</h2>
        <p>
          {{ t('attribution.opensubtitles.text') }}
          <a :href="links.opensubtitles" target="_blank" rel="noopener noreferrer">opensubtitles.org</a>.
        </p>
      </section>

      <section class="pc-section" data-test="pc-emby">
        <h2 class="pc-h2">Emby</h2>
        <p>{{ t('attribution.emby.text') }}</p>
      </section>

      <section class="pc-section" data-test="pc-imgur">
        <h2 class="pc-h2">Imgur</h2>
        <p>{{ t('attribution.imgur.text') }}</p>
      </section>

      <section class="pc-section" data-test="pc-youtube">
        <h2 class="pc-h2">YouTube</h2>
        <p>{{ t('attribution.youtube.text') }}</p>
      </section>

      <footer class="pc-footer" data-test="pc-footer">
        <p>
          MediaKeeper v{{ appVersion }} —
          <a :href="repoUrl" target="_blank" rel="noopener noreferrer">
            {{ t('attribution.githubLink') }}
          </a>
        </p>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import pkg from '../../../package.json'

const { t } = useI18n()

const appVersion = pkg.version
const repoUrl = 'https://github.com/KeeperD93/mediakeeper'

const links = {
  tmdb: 'https://www.themoviedb.org',
  opensubtitles: 'https://www.opensubtitles.org',
}

const tmdbLogoUrl = '/assets/icons/tmdb.svg'

const tmdbLegalText = 'This product uses the TMDB API but is not endorsed or certified by TMDB.'
</script>

<style scoped>
.pc-root {
  min-height: 100%;
  padding: 88px 16px 48px;
}

@media (max-width: 767px) {
  .pc-root { padding-top: 76px; }
}

.pc-inner {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.pc-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pc-title {
  margin: 0;
  font-size: var(--text-2xl, 24px);
  font-weight: var(--font-semibold, 600);
  color: var(--text-primary);
}

.pc-subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-sm, 14px);
}

.pc-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card, 12px);
  padding: 20px 22px;
  color: var(--text-secondary);
  line-height: 1.55;
}

.pc-section p {
  margin: 0;
}

.pc-section p + p {
  margin-top: 10px;
}

.pc-h2 {
  margin: 0 0 8px;
  font-size: var(--text-lg, 17px);
  color: var(--text-primary);
  font-weight: var(--font-semibold, 600);
}

.pc-tmdb {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}

.pc-tmdb-logo-link {
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
}

.pc-tmdb-logo-link:focus-visible {
  outline: 2px solid var(--accent-500, currentColor);
  outline-offset: 4px;
}

.pc-tmdb-logo {
  display: block;
  width: 120px;
  height: auto;
}

.pc-legal {
  max-width: 60ch;
  font-size: var(--text-sm, 14px);
}

.pc-footer {
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-xs, 12px);
  padding-top: 8px;
}

.pc-footer a {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.pc-section a {
  color: var(--accent-500);
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
