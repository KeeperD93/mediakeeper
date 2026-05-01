<template>
  <Teleport to="body">
    <transition name="pt-help-fade">
      <div
        v-if="visible"
        class="pt-help-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('portal.help.title')"
        @click.self="close"
        @keydown.esc.prevent="close"
      >
        <div class="pt-help-backdrop-fx" aria-hidden="true" />

        <div ref="panelRef" class="pt-help-panel" tabindex="-1">
          <button
            class="pt-help-close"
            type="button"
            :aria-label="$t('common.close')"
            @click="close"
          >
            <X :size="18" />
          </button>

          <aside class="pt-help-side">
            <header class="pt-help-side-head">
              <BookOpen :size="20" />
              <h2 class="pt-help-side-title">{{ $t('portal.help.title') }}</h2>
            </header>

            <div class="pt-help-search">
              <Search :size="16" class="pt-help-search-icon" />
              <input
                v-model="search"
                type="search"
                :placeholder="$t('portal.help.searchPlaceholder')"
                class="pt-help-search-input"
                :aria-label="$t('portal.help.searchPlaceholder')"
              />
            </div>

            <nav class="pt-help-cats" :aria-label="$t('portal.help.aria.categories')">
              <button
                v-for="cat in HELP_CATEGORIES"
                :key="cat"
                type="button"
                class="pt-help-cat"
                :class="{ 'pt-help-cat--active': activeCategory === cat }"
                :disabled="!categoryCounts[cat] && !search"
                @click="onSelectCategory(cat)"
              >
                <component :is="HELP_CATEGORY_ICON[cat]" :size="16" />
                <span class="pt-help-cat-label">{{ $t('portal.help.categories.' + cat) }}</span>
                <span class="pt-help-cat-count">{{ categoryCounts[cat] }}</span>
              </button>
            </nav>

            <div v-if="isAdmin" class="pt-help-admin-side">
              <button type="button" class="pt-help-admin-btn pt-help-admin-btn--add" @click="onCreate">
                <Plus :size="14" />
                {{ $t('portal.help.admin.add') }}
              </button>
              <button type="button" class="pt-help-admin-btn" @click="mode = 'trash'">
                <Trash2 :size="14" />
                {{ $t('portal.help.admin.trash') }}
              </button>
            </div>
          </aside>

          <section class="pt-help-content">
            <div v-if="loading" class="pt-help-state">
              <MkSpinner size="sm" inline />
              {{ $t('common.loading') }}
            </div>

            <div v-else-if="error" class="pt-help-state pt-help-state--error">
              {{ $t('portal.help.errorLoad') }}
            </div>

            <!-- Admin: Edit mode ─────────────────────────── -->
            <HelpEditView
              v-else-if="mode === 'edit' && editingArticle"
              :article="editingArticle"
            :lang="helpLang || 'fr'"
              @back="leaveEdit"
              @updated="onArticleUpdated"
              @deleted="onArticleDeleted"
            />

            <!-- Admin: Trash mode ────────────────────────── -->
            <HelpTrashView
              v-else-if="mode === 'trash'"
            :lang="helpLang || 'fr'"
              @back="mode = 'view'"
              @restored="reloadArticles"
              @purged="reloadArticles"
            />

            <!-- Search results across categories ──────── -->
            <div v-else-if="search.trim()" class="pt-help-results">
              <h3 class="pt-help-results-title">
                {{ $t('portal.help.searchResults', { count: filteredArticles.length }) }}
              </h3>
              <div v-if="!filteredArticles.length" class="pt-help-state pt-help-state--empty">
                {{ $t('portal.help.searchEmpty') }}
              </div>
              <HelpCardList
                v-else
                :articles="filteredArticles"
                :expanded-id="expandedId"
                :can-edit="isAdmin"
                show-category
                @toggle="onToggle"
                @edit="onEdit"
              />
            </div>

            <!-- Category list ──────────────────────────── -->
            <div v-else class="pt-help-results">
              <header class="pt-help-results-head">
                <component :is="HELP_CATEGORY_ICON[activeCategory]" :size="20" />
                <h3 class="pt-help-results-title">{{ $t('portal.help.categories.' + activeCategory) }}</h3>
                <span class="pt-help-results-count">{{ articlesInActiveCategory.length }}</span>
              </header>
              <div v-if="!articlesInActiveCategory.length" class="pt-help-state pt-help-state--empty">
                {{ $t('portal.help.categoryEmpty') }}
              </div>
              <HelpCardList
                v-else
                :articles="articlesInActiveCategory"
                :expanded-id="expandedId"
                :can-edit="isAdmin"
                @toggle="onToggle"
                @edit="onEdit"
              />
            </div>
          </section>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  BookOpen, Plus, Search, Trash2, X,
} from 'lucide-vue-next'

import MkSpinner from '@/components/common/MkSpinner.vue'
import HelpCardList from './help/HelpCardList.vue'
import HelpEditView from './help/HelpEditView.vue'
import HelpTrashView from './help/HelpTrashView.vue'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { usePortalHelp } from '@/composables/portal/usePortalHelp'
import { usePortalHelpAdmin } from '@/composables/portal/usePortalHelpAdmin'
import { HELP_CATEGORY_ICON } from '@/utils/portal/helpIconMap'

import '@/assets/styles/portal/help-overlay.css'
import '@/assets/styles/portal/help-overlay-content.css'
import '@/assets/styles/portal/help-overlay-admin.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  lang: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const visible = ref(false)
const panelRef = ref(null)
const mode = ref('view') // 'view' | 'edit' | 'trash'
const editingArticle = ref(null)
const expandedId = ref(null)

const { profile } = usePortalAuth()
const isAdmin = computed(() => profile.value?.role === 'admin')

const {
  HELP_CATEGORIES,
  loading, error, lang: helpLang,
  search, activeCategory, categoryCounts,
  filteredArticles, articlesInActiveCategory,
  load, selectCategory,
} = usePortalHelp()

function onToggle(id) {
  expandedId.value = expandedId.value === id ? null : id
}

const { createArticle } = usePortalHelpAdmin()

async function reloadArticles() {
  await load(props.lang || undefined, { admin: isAdmin.value })
}

function onSelectCategory(cat) {
  selectCategory(cat)
  mode.value = 'view'
  expandedId.value = null
}

function onEdit(article) {
  editingArticle.value = { ...article }
  mode.value = 'edit'
}

function leaveEdit() {
  mode.value = 'view'
  editingArticle.value = null
  reloadArticles()
}

async function onCreate() {
  const created = await createArticle({
    category: activeCategory.value || 'general',
    title: 'Nouvel article',
    body_html: '',
    lang: helpLang.value || 'fr',
    is_draft: true,
  })
  if (created?.id) {
    editingArticle.value = created
    mode.value = 'edit'
    await reloadArticles()
  }
}

function onArticleUpdated() {
  // No reload during editing: the auto-save debounce fires on every
  // keystroke, and refetching the article list mid-edit was racing the
  // editor's internal state and clobbering in-progress changes. The
  // sidebar list is refreshed when the admin leaves the edit view.
}

function onArticleDeleted() {
  mode.value = 'view'
  editingArticle.value = null
  reloadArticles()
}

function close() {
  visible.value = false
  setTimeout(() => emit('close'), 180)
}

function excerpt(html) {
  if (!html) return ''
  const text = String(html).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return text.length > 140 ? text.slice(0, 140) + '…' : text
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      visible.value = true
      mode.value = 'view'
      editingArticle.value = null
      expandedId.value = null
      await reloadArticles()
      await nextTick()
      panelRef.value?.focus?.()
    } else {
      visible.value = false
    }
  },
  { immediate: true },
)
</script>

<!-- Styles externalised to assets/styles/portal/help-overlay*.css; the
     extracted CSS keeps a unique class prefix to simulate Vue scoped CSS. -->
