<template>
  <section class="wzh-guides" :aria-labelledby="titleId">
    <div class="wzh-sh">
      <h2 :id="titleId" class="wzh-st">{{ $t('portal.wizardHelp.guides.title') }}</h2>
    </div>
    <ul class="wzh-guides-card">
      <li
        v-for="guide in HELP_GUIDES"
        :key="guide.slug"
        class="wzh-guide"
        :class="{ 'is-open': openSlug === guide.slug }"
      >
        <h3 class="wzh-guide-h">
          <button
            :id="`${uid}-${guide.key}-btn`"
            type="button"
            class="wzh-guide-btn"
            :aria-expanded="openSlug === guide.slug ? 'true' : 'false'"
            :aria-controls="openSlug === guide.slug ? `${uid}-${guide.key}-panel` : undefined"
            @click="toggle(guide.slug)"
          >
            <component :is="guide.icon" :size="18" class="wzh-guide-ic" aria-hidden="true" />
            <span class="wzh-guide-label">{{ $t(`portal.wizardHelp.guides.${guide.key}`) }}</span>
            <ChevronDown :size="16" class="wzh-guide-chev" aria-hidden="true" />
          </button>
        </h3>
        <div
          v-if="openSlug === guide.slug"
          :id="`${uid}-${guide.key}-panel`"
          class="wzh-guide-panel"
          role="region"
          :aria-labelledby="`${uid}-${guide.key}-btn`"
        >
          <p v-if="loading" class="wzh-guide-state">{{ $t('common.loading') }}</p>
          <p v-else-if="error" class="wzh-guide-state">
            {{ $t('portal.wizardHelp.guides.error') }}
            <button type="button" class="wzh-guide-retry" @click="ensureLoaded">
              {{ $t('portal.wizardHelp.guides.retry') }}
            </button>
          </p>
          <p v-else-if="!articleFor(guide.slug)" class="wzh-guide-state">
            {{ $t('portal.wizardHelp.guides.missing') }}
          </p>
          <!-- Same rendering as the Help Center: the server sanitises the body,
               then it is scrubbed again here. -->
          <!-- eslint-disable vue/no-v-html -->
          <div
            v-else
            class="wzh-guide-body pt-help-article-body"
            v-html="sanitizeHtml(articleFor(guide.slug).body_html)"
          />
          <!-- eslint-enable vue/no-v-html -->
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref, useId } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { HELP_GUIDES } from '@/constants/portalWizardHelp'
import { useHelpGuides } from '@/composables/portal/useHelpGuides'
import { sanitizeHtml } from '@/utils/sanitizeHtml'
import '@/assets/styles/portal/help-overlay-content.css'
import '@/assets/styles/portal/wizard-help-guides.css'

const uid = useId()
const titleId = `${uid}-title`
const openSlug = ref(null)
const { loading, error, ensureLoaded, articleFor } = useHelpGuides()

// One guide open at a time, like the Help Center.
function toggle(slug) {
  openSlug.value = openSlug.value === slug ? null : slug
  if (openSlug.value) ensureLoaded()
}
</script>
