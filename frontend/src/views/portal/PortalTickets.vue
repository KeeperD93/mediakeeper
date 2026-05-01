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

    <div class="ptl-filter-groups">
      <div v-for="g in filterGroups" :key="g.key" class="ptl-filter-group">
        <span class="ptl-filter-label">{{ $t(g.label) }}</span>
        <div class="arr-pills ptl-filter-pills">
          <button
            v-for="o in g.options" :key="`${g.key}-${o.value}`"
            type="button"
            class="arr-pill"
            :class="{ 'arr-pill--active': g.current === o.value }"
            @click="g.set(o.value)"
          >{{ $t(o.label) }}</button>
        </div>
      </div>
    </div>

    <p v-if="tickets.length" class="ptl-count">
      {{ $t('portal.tickets.list.count', tickets.length) }}
    </p>

    <div v-if="!tickets.length" class="ptl-empty">
      <span class="ptl-empty-icon">
        <CircleCheck :size="28" :stroke-width="1.6" aria-hidden="true" />
      </span>
      <p class="ptl-empty-title">{{ $t('portal.tickets.list.emptyTitle') }}</p>
      <p class="ptl-empty-sub">{{ $t('portal.tickets.list.emptySub') }}</p>
    </div>

    <div v-else class="ptl-list">
      <TicketCard
        v-for="t in tickets"
        :key="t.id"
        :ticket="t"
        @open="openTicket"
      />
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
                v-for="m in modes" :key="m.value"
                type="button"
                class="pt-mode-pill"
                :class="{ 'pt-mode-pill--active': mode === m.value }"
                @click="setMode(m.value)"
              >{{ $t(m.label) }}</button>
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
              <option v-for="it in issueTypes" :key="it" :value="it">
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
import { PORTAL_TAB } from '@/constants/portal'
import { CircleCheck, Plus, X } from 'lucide-vue-next'

import '@/assets/styles/portal/admin-rich-row-header.css'
import '@/assets/styles/portal/tickets-list.css'
import '@/assets/styles/portal/tickets-create-modal.css'

const { tickets, fetchTickets, createTicket } = usePortalTickets()
const { showToast } = useToast()
const { t } = useI18n()
const router = useRouter()

const showForm = ref(false)
const statusFilter = ref('')
const scopeFilter = ref('')
const issueFilter = ref('')
const ISSUE_TYPES = ['audio', 'subtitles', 'video', 'metadata', 'playback', 'file', 'other']
const modes = [
  { value: 'library', label: 'portal.tickets.picker.modeLibrary' },
  { value: 'other', label: 'portal.tickets.picker.modeOther' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'portal.tickets.list.allStatus' },
  { value: 'open', label: 'portal.tickets.status.open' },
  { value: 'in_progress', label: 'portal.tickets.status.in_progress' },
  { value: 'resolved', label: 'portal.tickets.status.resolved' },
  { value: 'closed', label: 'portal.tickets.status.closed' },
]
const SCOPE_OPTIONS = [
  { value: '', label: 'portal.tickets.list.allScopes' },
  { value: 'library', label: 'portal.tickets.list.scopeLibrary' },
  { value: 'movie', label: 'portal.tickets.list.scopeMovies' },
  { value: 'series', label: 'portal.tickets.list.scopeSeries' },
  { value: 'other', label: 'portal.tickets.list.scopeOther' },
]
const ISSUE_OPTIONS = [
  { value: '', label: 'portal.tickets.list.allTypes' },
  ...ISSUE_TYPES.map(it => ({ value: it, label: `portal.tickets.types.${it}` })),
]

const filterGroups = computed(() => [
  { key: 'status', label: 'portal.tickets.list.filterStatus',
    options: STATUS_OPTIONS, current: statusFilter.value, set: setStatus },
  { key: 'scope', label: 'portal.tickets.list.filterScope',
    options: SCOPE_OPTIONS, current: scopeFilter.value, set: setScope },
  { key: 'issue', label: 'portal.tickets.list.filterIssue',
    options: ISSUE_OPTIONS, current: issueFilter.value, set: setIssue },
])

// Map the user-facing scope choice to the backend ``media_type`` filter list.
function _scopeToMediaTypes(scope) {
  if (!scope) return []
  if (scope === 'library') return ['movie', 'series', 'season', 'episode']
  if (scope === 'series') return ['series', 'season', 'episode']
  if (scope === 'movie') return ['movie']
  if (scope === 'other') return ['other']
  return []
}

function buildFilters() {
  return {
    status: statusFilter.value || null,
    media_type: _scopeToMediaTypes(scopeFilter.value),
    issue_type: issueFilter.value ? [issueFilter.value] : [],
  }
}

const mode = ref('library')
const selectedHit = ref(null)
// Defaults to "whole series" until the user touches the season tree.
const seriesSelection = ref({ media_type: 'series', selected_seasons: null })
const form = reactive({
  media_title: '', issue_type: 'video', description: '',
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

async function setStatus(value) {
  statusFilter.value = value
  await fetchTickets(buildFilters())
}
async function setScope(value) {
  scopeFilter.value = value
  await fetchTickets(buildFilters())
}
async function setIssue(value) {
  issueFilter.value = value
  await fetchTickets(buildFilters())
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
    await fetchTickets(buildFilters())
  }
}

onMounted(() => fetchTickets())
</script>
