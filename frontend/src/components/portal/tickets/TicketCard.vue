<template>
  <article
    class="tcd"
    :class="`tcd--status-${ticket.status}`"
    role="button"
    tabindex="0"
    @click="$emit('open', ticket.id)"
    @keydown.enter.prevent="$emit('open', ticket.id)"
    @keydown.space.prevent="$emit('open', ticket.id)"
  >
    <!-- Visual: real Emby poster for library tickets, issue-icon badge for "other" -->
    <div v-if="posterId" class="tcd-visual">
      <img
        :src="`/api/emby/image/${posterId}?type=Primary`"
        class="tcd-poster"
        :alt="ticket.media_title"
        loading="lazy"
        @error="$event.target.style.display = 'none'"
      />
    </div>
    <div v-else class="tcd-visual tcd-visual--icon" :style="iconBg">
      <component :is="issueMeta.icon" :size="34" :stroke-width="1.8" />
    </div>

    <div class="tcd-body">
      <div class="tcd-meta-line">
        <span class="tcd-id">#{{ ticket.id }}</span>
        <span class="tcd-pill tcd-pill--issue">
          {{ $t(`portal.tickets.types.${ticket.issue_type}`) }}
        </span>
        <span class="tcd-pill" :class="`tcd-pill--status-${ticket.status}`">
          {{ $t(`portal.tickets.status.${ticket.status}`) }}
        </span>
        <span v-if="ticket.priority === 'blocking'" class="tcd-pill tcd-pill--blocking">
          {{ $t('portal.tickets.detail.priority.blocking') }}
        </span>
      </div>

      <h3 class="tcd-title">{{ ticket.media_title }}</h3>

      <p v-if="scopeLabel" class="tcd-scope">{{ scopeLabel }}</p>

      <div class="tcd-foot">
        <span v-if="ticket.created_at" class="tcd-foot-time">
          {{ formatRelative(ticket.created_at) }}
        </span>
        <span v-if="repliesCount" class="tcd-foot-replies">
          <MessageSquare :size="13" aria-hidden="true" />
          {{ $t('portal.tickets.list.replyCount', repliesCount) }}
        </span>
      </div>
    </div>

    <span class="tcd-chevron" aria-hidden="true">
      <ChevronRight :size="18" :stroke-width="2.2" />
    </span>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Captions,
  ChevronRight,
  FileText,
  HardDrive,
  HelpCircle,
  MessageSquare,
  MonitorPlay,
  PlayCircle,
  Volume2,
} from 'lucide-vue-next'

import '@/assets/styles/portal/ticket-card.css'

const props = defineProps({
  ticket: { type: Object, required: true },
})
defineEmits(['open'])

const { t } = useI18n()

const ISSUE_META = {
  audio: { icon: Volume2, color: '#f97316' },
  subtitles: { icon: Captions, color: '#22d3ee' },
  video: { icon: MonitorPlay, color: '#a855f7' },
  metadata: { icon: FileText, color: '#fbbf24' },
  playback: { icon: PlayCircle, color: '#f472b6' },
  file: { icon: HardDrive, color: '#94a3b8' },
  other: { icon: HelpCircle, color: '#818cf8' },
}
const issueMeta = computed(() => ISSUE_META[props.ticket.issue_type] || ISSUE_META.other)
const iconBg = computed(() => ({
  background: `radial-gradient(ellipse at center, ${issueMeta.value.color}40, ${issueMeta.value.color}10 70%)`,
  color: issueMeta.value.color,
}))

const posterId = computed(() => {
  const t = props.ticket
  if (t.media_type === 'other') return null
  return t.series_emby_id || t.emby_item_id || null
})

const repliesCount = computed(() => props.ticket.replies_count || 0)

const scopeLabel = computed(() => {
  const tk = props.ticket
  if (tk.media_type === 'movie' || tk.media_type === 'other' || tk.media_type === 'series') {
    return ''
  }
  const list = tk.selected_seasons || []
  if (!list.length) return ''
  const parts = list.map(entry => {
    if (!entry.episodes || !entry.episodes.length) {
      return t('portal.tickets.detail.scope.season', { n: entry.season_number })
    }
    return t('portal.tickets.detail.scope.episodes', {
      n: entry.season_number,
      list: entry.episodes.join(', '),
    })
  })
  return parts.join(' · ')
})

function formatRelative(iso) {
  if (!iso) return ''
  const diffSec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diffSec < 0) return t('common.timeAgo.justNow')
  if (diffSec < 60) return t('common.timeAgo.seconds', { n: diffSec })
  const m = Math.floor(diffSec / 60)
  if (m < 60) return t('common.timeAgo.minutes', { n: m })
  const h = Math.floor(m / 60)
  if (h < 24) return t('common.timeAgo.hours', { n: h })
  const d = Math.floor(h / 24)
  if (d < 30) return t('common.timeAgo.days', { n: d })
  return t('common.timeAgo.months', { n: Math.floor(d / 30) })
}
</script>
