<template>
  <Teleport to="body">
    <transition name="sm-fade">
      <div
        v-if="visible"
        class="sm-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="t('search.placeholder')"
        @click.self="close"
      >
        <div
          ref="modalRef"
          class="sm-modal"
          tabindex="-1"
          @click.stop
          @keydown="handleModalKeydown"
        >
          <!-- Search input -->
          <div class="sm-input-wrap">
            <Search class="sm-input-icon" :size="18" />
            <input
              ref="inputRef"
              v-model="query"
              class="sm-input"
              type="text"
              :placeholder="t('search.placeholder')"
              @keydown.down.prevent="moveDown"
              @keydown.up.prevent="moveUp"
              @keydown.enter.prevent="selectCurrent"
              @keydown.escape="close"
            />
            <button type="button" class="sm-close" :aria-label="t('common.close')" @click="close">
              <X :size="16" />
            </button>
            <kbd class="sm-esc">Esc</kbd>
          </div>

          <!-- Results -->
          <div v-if="filtered.length > 0" class="sm-results">
            <div
              v-for="(item, i) in filtered"
              :key="item.path"
              class="sm-item"
              :class="{ active: i === activeIndex }"
              @click="navigate(item)"
              @mouseenter="activeIndex = i"
            >
              <span class="sm-item-icon">
                <component :is="item.icon" :size="18" :stroke-width="1.8" />
              </span>
              <div class="sm-item-info">
                <span class="sm-item-title">{{ item.title }}</span>
                <span class="sm-item-sub">{{ item.subtitle }}</span>
              </div>
              <ChevronRight class="sm-item-arrow" :size="14" />
            </div>
          </div>

          <!-- Empty state -->
          <div v-else-if="query.length > 0" class="sm-empty">
            <p>{{ t('common.noResultsFor', { query }) }}</p>
          </div>

          <!-- Hints -->
          <div class="sm-footer">
            <span class="sm-hint">
              <kbd>↑↓</kbd>
              {{ t('search.navigate') }}
            </span>
            <span class="sm-hint">
              <kbd>↵</kbd>
              {{ t('search.open') }}
            </span>
            <span class="sm-hint">
              <kbd>esc</kbd>
              {{ t('search.closeHint') }}
            </span>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  BarChart3,
  Bell,
  ChevronRight,
  ClipboardCheck,
  Copy,
  FileText,
  Film,
  Home,
  MessageSquare,
  Search,
  Settings,
  Users,
  X,
} from 'lucide-vue-next'

import '@/assets/styles/search-modal.css'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])
const router = useRouter()

const query = ref('')
const activeIndex = ref(0)
const inputRef = ref(null)
const modalRef = ref(null)
let lastFocusedElement = null

const PAGE_ICONS = {
  '/': Home,
  '/stats': BarChart3,
  '/watchlist': ClipboardCheck,
  '/media-manager': Film,
  '/duplicates': Copy,
  '/notifications': Bell,
  '/tracker': Users,
  '/portal': MessageSquare,
  '/settings': Settings,
  '/logs': FileText,
}

const PAGES = computed(() => [
  {
    path: '/',
    title: t('sidebar.dashboard'),
    subtitle: t('dashboard.subtitle'),
    icon: PAGE_ICONS['/'],
  },
  {
    path: '/stats',
    title: t('sidebar.statistics'),
    subtitle: t('stats.title'),
    icon: PAGE_ICONS['/stats'],
  },
  {
    path: '/watchlist',
    title: t('sidebar.watchlist'),
    subtitle: t('watchlist.title'),
    icon: PAGE_ICONS['/watchlist'],
  },
  {
    path: '/media-manager',
    title: t('sidebar.mediaManager'),
    subtitle: t('mediaManager.title'),
    icon: PAGE_ICONS['/media-manager'],
  },
  {
    path: '/duplicates',
    title: t('sidebar.duplicates'),
    subtitle: t('duplicates.title'),
    icon: PAGE_ICONS['/duplicates'],
  },
  {
    path: '/notifications',
    title: t('sidebar.notifications'),
    subtitle: t('notifications.title'),
    icon: PAGE_ICONS['/notifications'],
  },
  {
    path: '/tracker',
    title: t('sidebar.tracker'),
    subtitle: t('sidebar.tracker'),
    icon: PAGE_ICONS['/tracker'],
  },
  {
    path: '/portal',
    title: t('sidebar.requests'),
    subtitle: t('sidebar.requests'),
    icon: PAGE_ICONS['/portal'],
  },
  {
    path: '/settings',
    title: t('sidebar.settings'),
    subtitle: t('settings.title'),
    icon: PAGE_ICONS['/settings'],
  },
  { path: '/logs', title: t('sidebar.logs'), subtitle: t('logs.title'), icon: PAGE_ICONS['/logs'] },
])

const filtered = computed(() => {
  if (!query.value) return PAGES.value
  const q = query.value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
  return PAGES.value.filter(p => {
    const t = (p.title + ' ' + p.subtitle)
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
    return t.includes(q)
  })
})

watch(query, () => {
  activeIndex.value = 0
})

watch(
  () => props.visible,
  async v => {
    if (v) {
      lastFocusedElement =
        document.activeElement instanceof HTMLElement ? document.activeElement : null
      query.value = ''
      activeIndex.value = 0
      await nextTick()
      inputRef.value?.focus()
    } else if (lastFocusedElement) {
      lastFocusedElement.focus?.()
      lastFocusedElement = null
    }
  },
)

onBeforeUnmount(() => {
  if (lastFocusedElement) lastFocusedElement.focus?.()
})

function moveDown() {
  if (activeIndex.value < filtered.value.length - 1) activeIndex.value++
}

function moveUp() {
  if (activeIndex.value > 0) activeIndex.value--
}

function selectCurrent() {
  const item = filtered.value[activeIndex.value]
  if (item) navigate(item)
}

function navigate(item) {
  router.push(item.path)
  close()
}

function close() {
  emit('close')
}

function handleModalKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (event.key !== 'Tab') return

  const focusable = modalRef.value?.querySelectorAll(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )
  const elements = Array.from(focusable || []).filter(el => el.offsetParent !== null)
  if (elements.length === 0) {
    event.preventDefault()
    modalRef.value?.focus?.()
    return
  }
  const currentIndex = elements.indexOf(document.activeElement)
  if (event.shiftKey) {
    if (currentIndex <= 0) {
      event.preventDefault()
      elements.at(-1)?.focus()
    }
    return
  }
  if (currentIndex === -1 || currentIndex === elements.length - 1) {
    event.preventDefault()
    elements[0]?.focus()
  }
}
</script>
