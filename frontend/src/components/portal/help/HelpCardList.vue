<template>
  <ul class="pt-help-list">
    <li
      v-for="a in articles"
      :key="a.id"
      class="pt-help-card"
      :class="{ 'pt-help-card--open': expandedId === a.id }"
    >
      <button type="button" class="pt-help-card-main" @click="$emit('toggle', a.id)">
        <span class="pt-help-card-icon">
          <component :is="helpIconFor(a.icon)" :size="18" />
        </span>
        <span class="pt-help-card-body">
          <span v-if="showCategory" class="pt-help-card-cat">
            {{ $t('portal.help.categories.' + a.category) }}
            <em v-if="a.is_draft" class="pt-help-card-draft">{{ $t('portal.help.admin.draft') }}</em>
          </span>
          <span class="pt-help-card-title">
            {{ a.title }}
            <em v-if="!showCategory && a.is_draft" class="pt-help-card-draft">{{ $t('portal.help.admin.draft') }}</em>
          </span>
          <span v-if="expandedId !== a.id" class="pt-help-card-excerpt">{{ excerpt(a.body_html) }}</span>
        </span>
        <ChevronDown :size="18" class="pt-help-card-chev" />
      </button>

      <button v-if="canEdit" type="button" class="pt-help-card-edit"
              :title="$t('portal.help.admin.edit')"
              @click.stop="$emit('edit', a)">
        <Pencil :size="14" />
      </button>

      <transition name="pt-help-accordion">
        <!-- Body is server-side sanitised HTML (bleach whitelist) and
             passed through DOMPurify here as defence in depth. -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
          v-if="expandedId === a.id"
          class="pt-help-card-content pt-help-article-body"
          v-html="purify(a.body_html)"
        />
      </transition>
    </li>
  </ul>
</template>

<script setup>
import DOMPurify from 'dompurify'
import { ChevronDown, Pencil } from 'lucide-vue-next'
import { helpIconFor } from '@/utils/portal/helpIconMap'

defineProps({
  articles: { type: Array, default: () => [] },
  expandedId: { type: [Number, null], default: null },
  canEdit: { type: Boolean, default: false },
  showCategory: { type: Boolean, default: false },
})
defineEmits(['toggle', 'edit'])

// Server already sanitises ``body_html`` with a strict bleach whitelist
// (services/portal/help_sanitize.py). Running it through DOMPurify here
// is belt-and-braces: if the backend ever regresses, the rendered HTML
// is still scrubbed before reaching the DOM.
function purify(html) {
  if (!html) return ''
  return DOMPurify.sanitize(String(html))
}

function excerpt(html) {
  if (!html) return ''
  const text = String(html).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return text.length > 140 ? text.slice(0, 140) + '…' : text
}
</script>
