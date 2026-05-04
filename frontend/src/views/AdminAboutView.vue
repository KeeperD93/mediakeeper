<template>
  <div class="ab-root mk-page-root">
    <div class="ab-inner">
      <header class="ab-header">
        <div class="ab-title-row">
          <h1 class="ab-title">{{ t('attribution.about.title') }}</h1>
          <span class="ab-current">v{{ appVersion }}</span>
        </div>
        <p class="ab-subtitle">{{ t('attribution.about.subtitle') }}</p>
      </header>

      <section class="ab-section" data-test="ab-stack">
        <h2 class="ab-h2">{{ t('attribution.about.stackTitle') }}</h2>
        <ul class="ab-list">
          <li>
            <strong>{{ t('attribution.about.backendLabel') }} :</strong>
            {{ stack.backend }}
          </li>
          <li>
            <strong>{{ t('attribution.about.frontendLabel') }} :</strong>
            {{ stack.frontend }}
          </li>
        </ul>
      </section>

      <section class="ab-section" data-test="ab-licenses">
        <h2 class="ab-h2">{{ t('attribution.about.licensesTitle') }}</h2>
        <p data-test="ab-ffmpeg">
          {{ t('attribution.about.ffmpegText') }}
          <a :href="links.ffmpegLegal" target="_blank" rel="noopener noreferrer">
            ffmpeg.org/legal.html
          </a>
          .
        </p>
        <p>
          {{ t('attribution.about.dependenciesText') }}
          <a :href="repoUrl" target="_blank" rel="noopener noreferrer">GitHub</a>
          .
        </p>
      </section>

      <section class="ab-section" data-test="ab-credits-link">
        <h2 class="ab-h2">{{ t('attribution.about.thirdPartyTitle') }}</h2>
        <p>
          {{ t('attribution.about.thirdPartyText') }}
          <router-link :to="{ name: 'portal-credits' }" target="_blank">
            /portal/credits
          </router-link>
          .
        </p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import pkg from '../../package.json'

const { t } = useI18n()

const appVersion = pkg.version
const repoUrl = 'https://github.com/KeeperD93/mediakeeper'

const stack = {
  backend: 'Python 3.12, FastAPI, SQLAlchemy, asyncpg, PostgreSQL',
  frontend: 'Vue 3, Vite, PrimeVue, Pinia',
}

const links = {
  ffmpegLegal: 'https://ffmpeg.org/legal.html',
}
</script>

<style scoped>
.ab-root {
  padding: 24px 24px 48px;
}

.ab-inner {
  max-width: 880px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ab-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ab-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ab-title {
  margin: 0;
  font-size: var(--text-2xl, 24px);
  color: var(--text-primary);
  font-weight: var(--font-semibold, 600);
}

.ab-current {
  font-size: var(--text-sm, 14px);
  color: var(--text-muted);
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-btn, 8px);
  padding: 2px 10px;
}

.ab-subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-sm, 14px);
}

.ab-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card, 12px);
  padding: 20px 22px;
  color: var(--text-secondary);
  line-height: 1.55;
}

.ab-section p {
  margin: 0;
}

.ab-section p + p {
  margin-top: 10px;
}

.ab-h2 {
  margin: 0 0 12px;
  font-size: var(--text-lg, 17px);
  color: var(--text-primary);
  font-weight: var(--font-semibold, 600);
}

.ab-list {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ab-section a {
  color: var(--accent-500);
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
