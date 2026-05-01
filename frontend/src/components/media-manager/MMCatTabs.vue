<template>
  <div class="mm-tabs-wrapper">
    <button v-show="canScrollLeft" class="mm-tabs-arrow mm-tabs-arrow-left" @click="scrollTabs('left')" @mouseenter="startAutoScroll('left')" @mouseleave="stopAutoScroll" @dragover.prevent="startAutoScroll('left')" @dragleave="stopAutoScroll" @drop.prevent="stopAutoScroll">
      <ChevronLeft :size="14" />
    </button>
    <div ref="tabsRef" class="mm-tabs" @scroll="updateScrollState">
      <button
        v-for="c in CATS" :key="c.key"
        class="mm-tab"
        :class="{
          active:    activeCat === c.key,
          'drop-hl': dragOverCat === c.key && draggedActive && activeCat !== c.key,
        }"
        @click="setCat(c.key)"
        @contextmenu.prevent="openDeleteMenu($event, c.key)"
        @dragover.prevent="onDragOverTab(c.key)"
        @dragleave="onDragLeaveTab"
        @drop.prevent="onDropTab(c.key)"
      >
        <Folder class="tab-icon" :size="15" :stroke-width="1.8" />
        {{ c.label }}
      </button>
      <button
        class="mm-tab mm-tab-all"
        :class="{ active: multiCatMode }"
        :title="$t('mediaManager.allCategoriesTitle')"
        @click="toggleMultiCat"
      >
        <List class="tab-icon" :size="15" :stroke-width="1.8" />
        {{ $t('mediaManager.allCategories') }}
      </button>
    </div>
    <button v-show="canScrollRight" class="mm-tabs-arrow mm-tabs-arrow-right" @click="scrollTabs('right')" @mouseenter="startAutoScroll('right')" @mouseleave="stopAutoScroll" @dragover.prevent="startAutoScroll('right')" @dragleave="stopAutoScroll" @drop.prevent="stopAutoScroll">
      <ChevronRight :size="14" />
    </button>
    <!-- Bouton + ajouter category -->
    <button class="mm-tabs-add" :title="$t('mediaManager.addCategoryTitle')" @click="showAddModal = true">
      <Plus :size="14" />
    </button>

    <!-- Modal ajout category -->
    <div v-if="showAddModal" class="mm-overlay show" @click.self="showAddModal = false">
      <div class="mm-cat-modal">
        <div class="mm-cat-modal-header">
          <span>{{ $t('mediaManager.addCategoryTitle') }}</span>
          <button class="mm-btn-sm mm-btn-sm--close" @click="showAddModal = false">
            <X :size="12" />
          </button>
        </div>
        <div class="mm-cat-modal-body">
          <div class="mm-cat-field">
            <label class="mm-cat-label">{{ $t('mediaManager.categoryName') }}</label>
            <input v-model="newCatLabel" class="mm-cat-input" :placeholder="$t('mediaManager.categoryNamePlaceholder')" />
          </div>
          <div class="mm-cat-field">
            <label class="mm-cat-label">{{ $t('mediaManager.categoryPath') }}</label>
            <!-- Breadcrumb navigation -->
            <div class="mm-browse-bc">
              <span class="mm-browse-crumb" @click="browseTo('/')">
                <Home :size="11" />
                /
              </span>
              <template v-for="(seg, i) in browseCrumbs" :key="i">
                <span class="mm-browse-sep">/</span>
                <span class="mm-browse-crumb" @click="browseTo(browseCrumbs.slice(0, i + 1).join('/'))">{{ seg }}</span>
              </template>
            </div>
            <!-- Liste des folders -->
            <div class="mm-browse-list">
              <div v-if="browseLoading" class="mm-browse-empty">
                <span class="mk-spin mk-spin--14" />
              </div>
              <div v-else-if="browseError" class="mm-browse-empty mm-browse-empty--error">{{ browseError }}</div>
              <div v-else-if="!browseDirs.length" class="mm-browse-empty">{{ $t('mediaManager.noSubfolders') }}</div>
              <div v-for="d in browseDirs" :key="d.path" class="mm-browse-item" :class="{ selected: newCatPath === d.path }" @click="selectDir(d)">
                <Folder :size="13" :stroke-width="1.8" />
                <span class="mm-browse-name">{{ d.name }}</span>
                <ChevronRight class="mm-browse-chevron" :size="10" />
              </div>
            </div>
            <!-- Selected path -->
            <div v-if="newCatPath" class="mm-browse-selected">
              <Check :size="11" />
              {{ newCatPath }}
            </div>
          </div>
        </div>
        <div class="mm-cat-modal-footer">
          <button class="mm-btn-sm" @click="showAddModal = false">{{ $t('common.cancel') }}</button>
          <button class="mm-btn-sm mm-btn-accent" :disabled="!newCatLabel.trim() || !newCatPath.trim()" @click="submitAdd">
            <Check :size="12" />
            {{ $t('common.add') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Menu contextuel deletion -->
    <div v-if="deleteMenu.show" class="mm-cat-ctx" :style="{ top: deleteMenu.y + 'px', left: deleteMenu.x + 'px' }" @click.self="deleteMenu.show = false">
      <button class="mm-cat-ctx-btn" @click="confirmDelete">
        <Trash2 :size="12" />
        {{ $t('mediaManager.deleteCategory') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaManager, CATS } from '@/composables/useMediaManager'
import { useApi } from '@/composables/useApi'
import { Check, ChevronLeft, ChevronRight, Folder, Home, List, Plus, Trash2, X } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

const { t } = useI18n()
const { apiGet } = useApi()
const { activeCat, dragOverCat, multiCatMode, setCat, dropOnCat, toggleMultiCat, addCategory, removeCategory } = useMediaManager()
const draggedActive = computed(() => dragOverCat.value !== null)

function onDragOverTab(key) { dragOverCat.value = key }
function onDragLeaveTab() { dragOverCat.value = null }
function onDropTab(key) { dragOverCat.value = null; dropOnCat(key) }

// ── Ajout category ──
const showAddModal = ref(false)
const newCatLabel = ref('')
const newCatPath = ref('')

// ── Browse folders ──
const browsePath = ref('/')
const browseDirs = ref([])
const browseLoading = ref(false)
const browseError = ref('')

const browseCrumbs = computed(() => {
  const p = browsePath.value.replace(/^\/+/, '').replace(/\/+$/, '')
  return p ? p.split('/') : []
})

async function loadBrowseDirs(path) {
  browseLoading.value = true
  browseError.value = ''
  try {
    const data = await apiGet(`/api/media/browse-dirs?path=${encodeURIComponent(path)}`)
    if (data?.error) { browseError.value = data.error; browseDirs.value = [] }
    else { browseDirs.value = data?.dirs || [] }
  } catch { browseError.value = t('common.networkError') }
  browseLoading.value = false
}

function browseTo(path) {
  const normalized = '/' + path.replace(/^\/+/, '').replace(/\/+$/, '')
  browsePath.value = normalized
  loadBrowseDirs(normalized)
}

function selectDir(d) {
  // Single click = select the path, double click (or chevron click) = navigate into it
  if (newCatPath.value === d.path) {
    // Already selected -> navigate into it
    browseTo(d.path)
  } else {
    newCatPath.value = d.path
  }
}

// Load the root folders when the modal opens
watch(showAddModal, (v) => {
  if (v) {
    browsePath.value = '/'
    newCatLabel.value = ''
    newCatPath.value = ''
    loadBrowseDirs('/')
  }
})

async function submitAdd() {
  if (!newCatLabel.value.trim() || !newCatPath.value.trim()) return
  const ok = await addCategory(newCatLabel.value.trim(), newCatPath.value.trim())
  if (ok) {
    newCatLabel.value = ''
    newCatPath.value = ''
    showAddModal.value = false
    nextTick(updateScrollState)
  }
}

// ── Deletion category (clic droit) ──
const deleteMenu = ref({ show: false, x: 0, y: 0, key: '' })

function openDeleteMenu(e, key) {
  deleteMenu.value = { show: true, x: e.clientX, y: e.clientY, key }
  const close = () => { deleteMenu.value.show = false; document.removeEventListener('click', close) }
  setTimeout(() => document.addEventListener('click', close), 10)
}

async function confirmDelete() {
  const key = deleteMenu.value.key
  deleteMenu.value.show = false
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('mediaManager.confirmDeleteTab'),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (ok) {
    await removeCategory(key)
    nextTick(updateScrollState)
  }
}

// ── Scroll ──
const tabsRef = ref(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
let _autoScrollTimer = null

function updateScrollState() {
  const el = tabsRef.value
  if (!el) return
  canScrollLeft.value = el.scrollLeft > 2
  canScrollRight.value = el.scrollLeft < el.scrollWidth - el.clientWidth - 2
}

function scrollTabs(dir) {
  const el = tabsRef.value
  if (!el) return
  el.scrollBy({ left: dir === 'left' ? -160 : 160, behavior: 'smooth' })
}

function startAutoScroll(dir) {
  stopAutoScroll()
  _autoScrollTimer = setInterval(() => {
    const el = tabsRef.value
    if (!el) return
    el.scrollBy({ left: dir === 'left' ? -40 : 40 })
  }, 50)
}

function stopAutoScroll() {
  if (_autoScrollTimer) { clearInterval(_autoScrollTimer); _autoScrollTimer = null }
}

let _resizeObs = null
onMounted(() => {
  nextTick(updateScrollState)
  _resizeObs = new ResizeObserver(updateScrollState)
  if (tabsRef.value) _resizeObs.observe(tabsRef.value)
})
onUnmounted(() => {
  stopAutoScroll()
  if (_resizeObs) _resizeObs.disconnect()
})

defineExpose({ tabsRef, startAutoScroll, stopAutoScroll })
</script>
