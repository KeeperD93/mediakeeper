<template>
  <div class="ptl">
    <header class="ptl-head">
      <div>
        <h1 class="ptl-title">{{ $t('portal.tickets.title') }}</h1>
        <p class="ptl-sub">{{ $t('portal.tickets.subtitle') }}</p>
      </div>
      <button class="ptl-create" type="button" @click="showForm = true">
        <Plus :size="16" :stroke-width="2.5" />
        {{ $t('portal.tickets.create') }}
      </button>
    </header>

    <div class="ptl-toolbar">
      <div class="arr-pills ptl-toolbar-pills">
        <button
          v-for="st in STATUS_OPTIONS"
          :key="`status-${st.value || 'all'}`"
          type="button"
          class="arr-pill"
          :class="{ 'arr-pill--active': statusFilter === st.value }"
          @click="setStatus(st.value)"
        >
          {{ $t(st.label) }}
        </button>
      </div>
      <div class="ptl-toolbar-selects">
        <select
          v-model="issueFilter"
          class="arr-sort ptl-toolbar-select"
          :aria-label="$t('portal.tickets.issueType')"
          @change="onIssueChange"
        >
          <option value="">{{ $t('portal.tickets.list.filterTypeAll') }}</option>
          <option v-for="it in ISSUE_TYPES" :key="it" :value="it">
            {{ $t(`portal.tickets.types.${it}`) }}
          </option>
        </select>
        <select
          v-model="sortOrder"
          class="arr-sort ptl-toolbar-select"
          :aria-label="$t('portal.tickets.list.sortLabel')"
          @change="onSortChange"
        >
          <option value="newest">{{ $t('portal.tickets.list.sortNewest') }}</option>
          <option value="oldest">{{ $t('portal.tickets.list.sortOldest') }}</option>
        </select>
        <PortalPagination
          :page="page"
          :per-page="perPage"
          :total="total"
          :disabled="loading"
          @update:page="onPage"
          @update:per-page="onPerPage"
        />
      </div>
    </div>

    <p v-if="total" class="ptl-count">
      {{ $t('portal.tickets.list.count', total) }}
    </p>

    <div v-if="!tickets.length" class="ptl-empty">
      <span class="ptl-empty-icon">
        <CircleCheck :size="28" :stroke-width="1.6" aria-hidden="true" />
      </span>
      <p class="ptl-empty-title">{{ $t('portal.tickets.list.emptyTitle') }}</p>
      <p class="ptl-empty-sub">{{ $t('portal.tickets.list.emptySub') }}</p>
    </div>

    <div v-else class="ptl-list">
      <TicketCard v-for="ticket in tickets" :key="ticket.id" :ticket="ticket" @open="openTicket" />
    </div>

    <Teleport v-if="showForm" to="body">
      <div class="pt-popup-overlay" @click.self="closeForm">
        <div class="pt-popup pt-popup--md">
          <div class="pt-popup-header">
            <h2>{{ $t('portal.tickets.create') }}</h2>
            <button class="pt-popup-close" @click="closeForm"><X :size="14" /></button>
          </div>
          <div class="pt-popup-body">
            <div class="pt-mode-pills">
              <button
                v-for="m in modes"
                :key="m.value"
                type="button"
                class="pt-mode-pill"
                :class="{ 'pt-mode-pill--active': mode === m.value }"
                @click="setMode(m.value)"
              >
                {{ $t(m.label) }}
              </button>
            </div>

            <template v-if="mode === 'library'">
              <label>{{ $t('portal.tickets.picker.label') }}</label>
              <EmbyMediaPicker v-model="selectedHit" />

              <template v-if="selectedHit?.type === 'series'">
                <label>{{ $t('portal.tickets.seasonPicker.label') }}</label>
                <TicketSeasonPicker
                  :series-id="selectedHit.id"
                  @update:selection="onSeriesSelection"
                />
              </template>
            </template>

            <template v-else>
              <label>{{ $t('portal.tickets.mediaTitle') }}</label>
              <input
                v-model="form.media_title"
                class="pt-input"
                maxlength="500"
                :placeholder="$t('portal.tickets.picker.otherPlaceholder')"
              />
            </template>

            <label>{{ $t('portal.tickets.issueType') }}</label>
            <select v-model="form.issue_type" class="pt-input">
              <option v-for="it in ISSUE_TYPES" :key="it" :value="it">
                {{ $t(`portal.tickets.types.${it}`) }}
              </option>
            </select>

            <label>{{ $t('portal.tickets.description') }}</label>
            <textarea v-model="form.description" class="pt-input" rows="4" maxlength="2000" />
          </div>
          <div class="pt-popup-footer">
            <button class="pt-btn pt-btn--primary" :disabled="!canSubmit" @click="submit">
              {{ $t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortalTickets } from '@/composables/portal/usePortalTickets'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import TicketCard from '@/components/portal/tickets/TicketCard.vue'
import EmbyMediaPicker from '@/components/portal/tickets/EmbyMediaPicker.vue'
import TicketSeasonPicker from '@/components/portal/tickets/TicketSeasonPicker.vue'
import PortalPagination from '@/components/portal/PortalPagination.vue'
import { PORTAL_TAB } from '@/constants/portal'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'
import { CircleCheck, Plus, X } from 'lucide-vue-next'

import '@/assets/styles/portal/admin-rich-row-header.css'
import '@/assets/styles/portal/tickets-list.css'
import '@/assets/styles/portal/tickets-create-modal.css'

const { tickets, total, fetchTickets, createTicket, loading } = usePortalTickets()
const { showToast } = useToast()
const { t } = useI18n()
const router = useRouter()

const showForm = ref(false)
const statusFilter = ref('')
const issueFilter = ref('')
const sortOrder = ref('newest')
const page = ref(1)
const perPage = ref(DEFAULT_PAGE_SIZE)
const ISSUE_TYPES = ['audio', 'subtitles', 'video', 'metadata', 'playback', 'file', 'other']
const modes = [
  { value: 'library', label: 'portal.tickets.picker.modeLibrary' },
  { value: 'other', label: 'portal.tickets.picker.modeOther' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'portal.tickets.status.all' },
  { value: 'open', label: 'portal.tickets.status.open' },
  { value: 'in_progress', label: 'portal.tickets.status.in_progress' },
  { value: 'resolved', label: 'portal.tickets.status.resolved' },
  { value: 'closed', label: 'portal.tickets.status.closed' },
]

function buildFilters() {
  return {
    status: statusFilter.value || null,
    issueTypes: issueFilter.value ? [issueFilter.value] : null,
    sort: sortOrder.value,
    page: page.value,
    perPage: perPage.value,
  }
}

const mode = ref('library')
const selectedHit = ref(null)
// Defaults to "whole series" until the user touches the season tree.
const seriesSelection = ref({ media_type: 'series', selected_seasons: null })
const form = reactive({
  media_title: '',
  issue_type: 'video',
  description: '',
})

const canSubmit = computed(() => {
  if (!form.description.trim()) return false
  if (mode.value === 'library') return !!selectedHit.value
  return !!form.media_title.trim()
})

function setMode(value) {
  if (mode.value === value) return
  mode.value = value
  // Switching modes resets the anchor — keeps the payload coherent and
  // avoids a stale Emby selection sneaking into an "other" submission.
  selectedHit.value = null
  seriesSelection.value = { media_type: 'series', selected_seasons: null }
  form.media_title = ''
}

function onSeriesSelection(payload) {
  seriesSelection.value = payload
}

function closeForm() {
  showForm.value = false
  resetForm()
}

function resetForm() {
  mode.value = 'library'
  selectedHit.value = null
  seriesSelection.value = { media_type: 'series', selected_seasons: null }
  form.media_title = ''
  form.issue_type = 'video'
  form.description = ''
}

async function load() {
  await fetchTickets(buildFilters())
}
// Any status/type/sort/size change returns to the first page.
async function reload() {
  page.value = 1
  await load()
}
async function setStatus(value) {
  statusFilter.value = value
  await reload()
}
function onIssueChange() {
  reload()
}
function onSortChange() {
  reload()
}
function onPage(p) {
  page.value = p
  load()
}
function onPerPage(size) {
  perPage.value = size
  reload()
}

function openTicket(id) {
  router.push({ name: PORTAL_TAB.TICKET_DETAIL, params: { id } })
}

function buildPayload() {
  if (mode.value === 'other') {
    return {
      media_title: form.media_title.trim(),
      media_type: 'other',
      issue_type: form.issue_type,
      description: form.description.trim(),
    }
  }
  // Library mode — anchor + media_type derived from the picker hit. For
  // series, the season picker may narrow media_type to "season"/"episode"
  // and attach the granular ``selected_seasons`` payload.
  const hit = selectedHit.value
  const base = {
    media_title: hit.title,
    media_type: hit.type,
    tmdb_id: hit.tmdb_id ? Number(hit.tmdb_id) : null,
    issue_type: form.issue_type,
    description: form.description.trim(),
  }
  if (hit.type === 'movie') {
    base.emby_item_id = hit.id
  } else {
    base.series_emby_id = hit.id
    base.media_type = seriesSelection.value.media_type
    if (seriesSelection.value.selected_seasons) {
      base.selected_seasons = seriesSelection.value.selected_seasons
    }
  }
  return base
}

async function submit() {
  const res = await createTicket(buildPayload())
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    closeForm()
    await reload()
  }
}

onMounted(load)
</script>
