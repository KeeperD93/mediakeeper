<template>
  <div class="pt-cal-wrap">
    <button
      ref="btnRef"
      class="pt-nav-icon pt-cal-trigger"
      :title="$t('portal.mkCalendar.title')"
      @click="toggle"
    >
      <Calendar :size="20" stroke-width="1.8" />
    </button>

    <Teleport to="body">
      <transition name="pt-cal-pop">
        <div v-if="open" class="pt-cal-popup" :style="popupStyle" @click.stop>
          <header class="pt-cal-head">
            <h3>{{ $t('portal.mkCalendar.upcoming') }}</h3>
            <button class="pt-cal-x" :aria-label="$t('common.close')" @click="close">
              <X :size="16" :stroke-width="2.5" />
            </button>
          </header>
          <div class="pt-cal-list">
            <div v-if="loading" class="pt-cal-empty">{{ $t('common.loading') }}</div>
            <div v-else-if="!sortedEvents.length" class="pt-cal-empty">
              {{ $t('portal.mkCalendar.empty') }}
            </div>
            <button
              v-for="ev in sortedEvents"
              :key="ev.id"
              class="pt-cal-item"
              :class="`pt-cal-item--${statusClass(ev)}`"
              @click="openDetail(ev)"
            >
              <div class="pt-cal-date">
                <span class="pt-cal-day">{{ formatDay(ev.scheduled_at) }}</span>
                <span class="pt-cal-month">{{ formatMonth(ev.scheduled_at) }}</span>
                <span class="pt-cal-time">{{ formatTime(ev.scheduled_at) }}</span>
              </div>
              <div class="pt-cal-body">
                <div class="pt-cal-title">{{ ev.title }}</div>
                <div class="pt-cal-meta">
                  <span class="pt-cal-kind" :class="`pt-cal-kind--${ev.kind}`">
                    {{ $t(`portal.mkCalendar.kind.${ev.kind}`) }}
                  </span>
                  <span v-if="ev.tmdb_ids?.length > 1" class="pt-cal-marathon">
                    {{ $t('portal.mkCalendar.marathon', { n: ev.tmdb_ids.length }) }}
                  </span>
                </div>
              </div>
              <span class="pt-cal-status-pill" :title="statusLabel(ev)" />
            </button>
          </div>
        </div>
      </transition>
      <div v-if="open" class="pt-cal-shade" @click="close" />
    </Teleport>

    <EventDetailModal v-if="detailEventId" :event-id="detailEventId" @close="onDetailClose" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Calendar, X } from 'lucide-vue-next'
import { useRooms } from '@/composables/portal/useRooms'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import EventDetailModal from './EventDetailModal.vue'
import { EVENT_STATUS, EVENT_KIND, INVITATION_STATUS } from '@/constants/events'
import { localizedDate, localizedTime } from '@/utils/datetime'

import '@/assets/styles/portal/calendar-button.css'

const { t } = useI18n()
const { events, loading, fetchAll } = useRooms()
const { profile } = usePortalAuth()

const open = ref(false)
const detailEventId = ref(null)
const btnRef = ref(null)
const popupStyle = ref({})

// Anchor the popup to the trigger button's rect. The nav has a
// max-width so on wide viewports the button sits far from the viewport's
// right edge — a static `right: 2rem` drifts the popup away from it.
function computePopupStyle() {
  const el = btnRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  // On mobile the trigger is hidden (display: none) because the action
  // now lives in the avatar menu — rect comes back at 0×0. Fall back to a
  // fixed anchor just below the top bar so the popup stays reachable.
  if (rect.width === 0 || rect.height === 0) {
    popupStyle.value = { top: '64px', right: '8px' }
    return
  }
  const rightOffset = Math.max(8, window.innerWidth - rect.right)
  popupStyle.value = {
    top: `${Math.round(rect.bottom + 8)}px`,
    right: `${Math.round(rightOffset)}px`,
  }
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    computePopupStyle()
    await fetchAll()
  }
}
function close() {
  open.value = false
}

// Exposed so PortalNav's avatar menu can open the calendar on mobile —
// the visible trigger is hidden there to free up space in the top bar.
async function openFromMenu() {
  if (!open.value) await toggle()
}
defineExpose({ open: openFromMenu })
function onResize() {
  if (open.value) computePopupStyle()
}
function openDetail(ev) {
  detailEventId.value = ev.id
  close()
}
function onDetailClose() {
  detailEventId.value = null
  fetchAll()
}

// Filter out past events + cancelled, sort ascending by scheduled_at.
const sortedEvents = computed(() => {
  const now = Date.now()
  return [...events.value]
    .filter(e => e.status === EVENT_STATUS.SCHEDULED)
    .filter(e => new Date(e.scheduled_at).getTime() > now - 3600 * 1000)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
})

function myInvitation(ev) {
  if (!profile.value) return null
  return ev.invitations?.find(i => i.user_id === (profile.value.user_id || profile.value.id))
}

function statusClass(ev) {
  const inv = myInvitation(ev)
  if (!inv && ev.kind === EVENT_KIND.PUBLIC) return 'pending-public'
  if (!inv) return 'pending'
  if (inv.status === INVITATION_STATUS.ACCEPTED)
    return ev.kind === EVENT_KIND.PUBLIC ? 'accepted-public' : 'accepted-private'
  if (inv.status === INVITATION_STATUS.DECLINED) return 'declined'
  return 'pending'
}
function statusLabel(ev) {
  return t(`portal.mkCalendar.status.${statusClass(ev)}`)
}

function formatDay(iso) {
  return new Date(iso).getDate().toString().padStart(2, '0')
}
function formatMonth(iso) {
  return localizedDate(new Date(iso), { month: 'short' })
}
function formatTime(iso) {
  return localizedTime(new Date(iso), { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  fetchAll()
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onResize, { passive: true })
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onResize)
})
</script>
