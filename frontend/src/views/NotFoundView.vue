<template>
  <a href="#main-content" class="mk-skip-link">{{ t('common.skipToMain') }}</a>
  <main
    id="main-content"
    ref="pageRef"
    tabindex="-1"
    class="not-found-page"
    role="main"
    data-test="not-found-page"
  >
    <div class="not-found-card">
      <p class="not-found-code" aria-hidden="true">404</p>
      <h1 class="not-found-title">{{ t('errors.notFoundTitle') }}</h1>
      <p class="not-found-desc">{{ t('errors.notFoundDescription') }}</p>
      <div class="not-found-actions">
        <router-link
          v-if="isPortalRoute"
          :to="{ path: '/portal' }"
          class="not-found-cta"
          data-test="not-found-cta-portal"
        >
          {{ t('errors.notFoundCtaPortal') }}
        </router-link>
        <router-link
          v-else
          :to="{ path: '/' }"
          class="not-found-cta"
          data-test="not-found-cta-home"
        >
          {{ t('errors.notFoundCtaHome') }}
        </router-link>
      </div>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const pageRef = ref(null)
const isPortalRoute = computed(() => route.path.startsWith('/portal'))

onMounted(() => {
  pageRef.value?.focus?.()
})
</script>

<style scoped>
.not-found-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.not-found-card {
  width: 100%;
  max-width: 32rem;
  padding: 2.5rem 2rem;
  text-align: center;
  background: var(--surface-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-card);
}

.not-found-code {
  font-size: var(--text-3xl, 2rem);
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin: 0 0 0.5rem;
}

.not-found-title {
  font-size: var(--text-xl, 1.25rem);
  font-weight: 600;
  margin: 0 0 0.75rem;
  color: var(--text-primary);
}

.not-found-desc {
  font-size: var(--text-sm, 0.875rem);
  line-height: 1.5;
  color: var(--text-muted);
  margin: 0 0 1.75rem;
}

.not-found-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
}

.not-found-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 1.25rem;
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  text-decoration: none;
  color: #fff;
  background: var(--accent-500);
  border: 1px solid var(--accent-600);
  border-radius: var(--radius-btn);
  transition:
    background 0.15s ease,
    transform 0.15s ease;
}

.not-found-cta:hover {
  background: var(--accent-600);
}

.not-found-cta:focus-visible {
  outline: 2px solid var(--accent-300);
  outline-offset: 2px;
}
</style>
