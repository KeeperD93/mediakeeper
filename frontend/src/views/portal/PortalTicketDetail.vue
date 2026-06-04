<template>
  <div v-if="currentTicket" class="ptd">
    <button class="ptd-back" @click="$router.back()">← {{ $t('common.back') }}</button>

    <!-- Hero — only when the ticket points to a real library item.
         "Other" tickets get the compact card layout below directly. -->
    <header v-if="hasMedia" class="ptd-hero" :style="backdropStyle">
      <div class="ptd-hero-overlay" />
      <div class="ptd-hero-inner">
        <img
          v-if="posterId"
          :src="`/api/emby/image/${posterId}?type=Primary`"
          class="ptd-hero-poster"
          :alt="currentTicket.media_title"
          loading="lazy"
          @error="$event.target.style.display = 'none'"
        />
        <div class="ptd-hero-meta">
          <div class="ptd-hero-id">#{{ currentTicket.id }}</div>
          <h1 class="ptd-hero-title">{{ currentTicket.media_title }}</h1>
          <div class="ptd-hero-pills">
            <span class="ptd-pill ptd-pill--kind">
              {{ $t(`portal.tickets.detail.kind.${currentTicket.media_type}`) }}
            </span>
            <span class="ptd-pill" :class="`ptd-pill--status-${currentTicket.status}`">
              {{ $t(`portal.tickets.status.${currentTicket.status}`) }}
            </span>
            <span class="ptd-pill" :class="`ptd-pill--priority-${currentTicket.priority}`">
              {{ $t(`portal.tickets.detail.priority.${currentTicket.priority}`) }}
            </span>
            <span class="ptd-pill ptd-pill--issue">
              {{ $t(`portal.tickets.types.${currentTicket.issue_type}`) }}
            </span>
          </div>
          <p v-if="scopeLabel" class="ptd-hero-scope">{{ scopeLabel }}</p>
        </div>
      </div>
    </header>

    <!-- Compact header for "other" tickets -->
    <header v-else class="ptd-other-header">
      <div class="ptd-hero-id">#{{ currentTicket.id }}</div>
      <h1 class="ptd-other-title">{{ currentTicket.media_title }}</h1>
      <div class="ptd-hero-pills">
        <span class="ptd-pill ptd-pill--kind">
          {{ $t('portal.tickets.detail.kind.other') }}
        </span>
        <span class="ptd-pill" :class="`ptd-pill--status-${currentTicket.status}`">
          {{ $t(`portal.tickets.status.${currentTicket.status}`) }}
        </span>
        <span class="ptd-pill" :class="`ptd-pill--priority-${currentTicket.priority}`">
          {{ $t(`portal.tickets.detail.priority.${currentTicket.priority}`) }}
        </span>
        <span class="ptd-pill ptd-pill--issue">
          {{ $t(`portal.tickets.types.${currentTicket.issue_type}`) }}
        </span>
      </div>
    </header>

    <!-- Admin status control + timestamps -->
    <section class="ptd-toolbar">
      <div class="ptd-timestamps">
        <span>
          {{ $t('portal.tickets.detail.openedAt') }}: {{ formatDate(currentTicket.created_at) }}
        </span>
        <span
          v-if="currentTicket.updated_at && currentTicket.updated_at !== currentTicket.created_at"
        >
          · {{ $t('portal.tickets.detail.updatedAt') }}: {{ formatDate(currentTicket.updated_at) }}
        </span>
      </div>
      <div v-if="isAdmin" class="ptd-status-control">
        <label class="ptd-status-label">{{ $t('portal.tickets.detail.changeStatus') }}</label>
        <select class="ptd-status-select" :value="currentTicket.status" @change="onStatusChange">
          <option v-for="s in statusOptions" :key="s" :value="s">
            {{ $t(`portal.tickets.status.${s}`) }}
          </option>
        </select>
      </div>
    </section>

    <!-- Premium conversation thread -->
    <TicketThread :ticket="currentTicket" @reply="onReply" />
  </div>
  <div v-else class="ptd-loading">{{ $t('common.loading') }}</div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePortalTickets } from '@/composables/portal/usePortalTickets'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { USER_ROLE } from '@/constants/auth'
import TicketThread from '@/components/portal/tickets/TicketThread.vue'
import { localizedDateTime } from '@/utils/datetime'

import '@/assets/styles/portal/ticket-detail.css'

const route = useRoute()
const { t } = useI18n()
const { profile } = usePortalAuth()
const { currentTicket, fetchTicket, replyTicket, updateStatus } = usePortalTickets()
const { showToast } = useToast()

const statusOptions = ['open', 'in_progress', 'resolved', 'closed']

const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)

const hasMedia = computed(() => {
  const t = currentTicket.value
  return !!t && t.media_type !== 'other' && (t.emby_item_id || t.series_emby_id)
})

// Posters live on the series for series/season/episode tickets, and on
// the movie itself for movie tickets.
const posterId = computed(() => {
  const t = currentTicket.value
  if (!t) return null
  return t.series_emby_id || t.emby_item_id || null
})

const backdropStyle = computed(() => {
  if (!posterId.value) return {}
  return {
    backgroundImage: `url(/api/emby/image/${posterId.value}?type=Backdrop)`,
  }
})

const scopeLabel = computed(() => {
  const tk = currentTicket.value
  if (!tk) return ''
  if (tk.media_type === 'series') {
    return t('portal.tickets.detail.scope.wholeSeries')
  }
  const list = tk.selected_seasons || []
  if (!list.length) return ''
  const parts = list.map(entry => {
    const season = entry.season_number
    if (!entry.episodes || !entry.episodes.length) {
      return t('portal.tickets.detail.scope.season', { n: season })
    }
    return t('portal.tickets.detail.scope.episodes', {
      n: season,
      list: entry.episodes.join(', '),
    })
  })
  return parts.join(' · ')
})

function formatDate(iso) {
  if (!iso) return ''
  return localizedDateTime(new Date(iso))
}

async function onReply(content) {
  await replyTicket(currentTicket.value.id, content)
  showToast(t('common.success'), TOAST_TYPE.OK)
  await fetchTicket(route.params.id)
}

async function onStatusChange(e) {
  const next = e.target.value
  if (!next || next === currentTicket.value.status) return
  const res = await updateStatus(currentTicket.value.id, next)
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    await fetchTicket(route.params.id)
  }
}

onMounted(() => fetchTicket(route.params.id))
</script>
