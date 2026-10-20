<template>
  <Teleport to="body">
    <div class="pt-popup-overlay" @click.self="close">
      <div
        ref="panelRef"
        class="pt-popup pt-popup--md pt-popup--ticket"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`${uid}-title`"
        tabindex="-1"
      >
        <div class="pt-popup-header">
          <h2 :id="`${uid}-title`">{{ $t('portal.tickets.create') }}</h2>
          <button
            type="button"
            class="pt-popup-close"
            :aria-label="$t('common.close')"
            @click="close"
          >
            <X :size="14" />
          </button>
        </div>
        <div class="pt-popup-body">
          <div class="pt-mode-pills">
            <button
              v-for="m in MODES"
              :key="m.value"
              type="button"
              class="pt-mode-pill"
              :class="{ 'pt-mode-pill--active': mode === m.value }"
              :aria-pressed="mode === m.value ? 'true' : 'false'"
              @click="setMode(m.value)"
            >
              {{ $t(m.label) }}
            </button>
          </div>

          <template v-if="mode === TICKET_SOURCE.LIBRARY">
            <label :for="`${uid}-media`">{{ $t('portal.tickets.picker.label') }}</label>
            <EmbyMediaPicker v-model="selectedHit" :input-id="`${uid}-media`" />

            <template v-if="selectedHit?.type === 'series'">
              <span :id="`${uid}-seasons`" class="pt-popup-label">
                {{ $t('portal.tickets.seasonPicker.label') }}
              </span>
              <TicketSeasonPicker
                role="group"
                :aria-labelledby="`${uid}-seasons`"
                :series-id="selectedHit.id"
                @update:selection="seriesSelection = $event"
              />
            </template>
          </template>

          <template v-else>
            <label :for="`${uid}-title-input`">{{ $t('portal.tickets.mediaTitle') }}</label>
            <input
              :id="`${uid}-title-input`"
              v-model="form.media_title"
              class="pt-input"
              maxlength="500"
              :placeholder="$t('portal.tickets.picker.otherPlaceholder')"
            />
          </template>

          <label :for="`${uid}-issue`">{{ $t('portal.tickets.issueType') }}</label>
          <select
            :id="`${uid}-issue`"
            v-model="form.issue_type"
            class="pt-popup-select mk-select-chevron"
          >
            <option v-for="it in TICKET_ISSUE_TYPES" :key="it" :value="it">
              {{ $t(`portal.tickets.types.${it}`) }}
            </option>
          </select>

          <label :for="`${uid}-description`">{{ $t('portal.tickets.description') }}</label>
          <textarea
            :id="`${uid}-description`"
            v-model="form.description"
            class="pt-input"
            rows="4"
            maxlength="2000"
          />
        </div>
        <div class="pt-popup-footer">
          <button
            type="button"
            class="pt-btn pt-btn--primary"
            :disabled="!canSubmit || busy"
            @click="emit('submit', buildPayload())"
          >
            {{ $t('common.save') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
// The "report an issue" form: a library pick (movie, or series narrowed to
// seasons / episodes) or a title typed by hand. Mounted while open, so each
// opening starts blank; the page sends the payload.
import { computed, reactive, ref, useId } from 'vue'
import { X } from 'lucide-vue-next'
import EmbyMediaPicker from '@/components/portal/tickets/EmbyMediaPicker.vue'
import TicketSeasonPicker from '@/components/portal/tickets/TicketSeasonPicker.vue'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { TICKET_ISSUE_TYPES, TICKET_SOURCE } from '@/constants/tickets'

import '@/assets/styles/portal/tickets-create-modal.css'

const props = defineProps({
  // The page is sending the ticket: no second submit meanwhile, and the form
  // stays open so a failed send keeps what was typed.
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'submit'])

const MODES = [
  { value: TICKET_SOURCE.LIBRARY, label: 'portal.tickets.picker.modeLibrary' },
  { value: TICKET_SOURCE.OTHER, label: 'portal.tickets.picker.modeOther' },
]
const WHOLE_SERIES = { media_type: 'series', selected_seasons: null }

const uid = useId()
const panelRef = ref(null)
const mode = ref(TICKET_SOURCE.LIBRARY)
const selectedHit = ref(null)
// "Whole series" until the season tree is touched.
const seriesSelection = ref(WHOLE_SERIES)
const form = reactive({ media_title: '', issue_type: 'video', description: '' })

const canSubmit = computed(() => {
  if (!form.description.trim()) return false
  if (mode.value === TICKET_SOURCE.LIBRARY) return !!selectedHit.value
  return !!form.media_title.trim()
})

function setMode(value) {
  if (mode.value === value) return
  mode.value = value
  // A new source drops the previous one: no stale Emby pick in an "other" ticket.
  selectedHit.value = null
  seriesSelection.value = WHOLE_SERIES
  form.media_title = ''
}

function buildPayload() {
  const common = { issue_type: form.issue_type, description: form.description.trim() }
  if (mode.value === TICKET_SOURCE.OTHER) {
    return { ...common, media_title: form.media_title.trim(), media_type: TICKET_SOURCE.OTHER }
  }
  // A series pick may be narrowed to seasons / episodes by the season tree.
  const hit = selectedHit.value
  const base = {
    ...common,
    media_title: hit.title,
    media_type: hit.type,
    tmdb_id: hit.tmdb_id ? Number(hit.tmdb_id) : null,
  }
  if (hit.type === 'movie') return { ...base, emby_item_id: hit.id }
  const { media_type, selected_seasons } = seriesSelection.value
  return {
    ...base,
    series_emby_id: hit.id,
    media_type,
    ...(selected_seasons ? { selected_seasons } : {}),
  }
}

function close() {
  if (!props.busy) emit('close')
}

// Escape first closes the media picker's open suggestions, then the form
// (an expanded season toggle does not hold it back).
function onEscape() {
  const focused = document.activeElement
  if (
    focused?.getAttribute('role') === 'combobox' &&
    focused.getAttribute('aria-expanded') === 'true'
  )
    return
  close()
}

useFocusTrap({ active: ref(true), containerRef: panelRef, onEscape })
</script>
