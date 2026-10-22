<template>
  <div class="ab-root mk-page-root">
    <div class="ab-inner">
      <header class="ab-header">
        <h1 class="ab-title">{{ t('attribution.about.title') }}</h1>
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

const { t } = useI18n()

const repoUrl = 'https://github.com/KeeperD93/mediakeeper'

const stack = {
  backend: 'Python 3.14, FastAPI, SQLAlchemy, asyncpg, PostgreSQL',
  frontend: 'Vue 3, Vite',
}

const links = {
  ffmpegLegal: 'https://ffmpeg.org/legal.html',
}
</script>

<style scoped>
.ab-root {
  padding: var(--space-6) var(--space-6) calc(var(--space-6) * 2);
}

.ab-inner {
  max-width: 880px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.ab-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ab-title {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.ab-subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.ab-section {
  background: var(--bg-secondary);
  border: var(--border-width) solid var(--border);
  border-radius: var(--radius-card);
  padding: var(--space-5);
  color: var(--text-secondary);
  line-height: var(--lh-normal);
}

.ab-section p {
  margin: 0;
}

.ab-section p + p {
  margin-top: var(--space-2-5);
}

.ab-h2 {
  margin: 0 0 var(--space-3);
  font-size: var(--text-lg);
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.ab-list {
  margin: 0;
  padding-left: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* The lighter accent shade keeps the links readable on the dark card. */
.ab-section a {
  color: var(--accent-300);
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
