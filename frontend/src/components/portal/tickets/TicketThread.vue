<template>
  <section class="tth">
    <h2 class="tth-title">{{ $t('portal.tickets.thread.title') }}</h2>

    <!-- Empty state -->
    <div v-if="!entries.length" class="tth-empty">
      <MessageSquare :size="36" :stroke-width="1.5" aria-hidden="true" />
      <p>{{ $t('portal.tickets.thread.empty') }}</p>
    </div>

    <!-- Bubbles -->
    <ol v-else ref="listEl" class="tth-list" :aria-label="$t('portal.tickets.thread.title')">
      <li
        v-for="entry in entries"
        :key="entry.key"
        class="tth-row"
        :class="[
          entry.mine ? 'tth-row--mine' : 'tth-row--other',
          entry.isAdmin ? 'tth-row--admin' : null,
          entry.deleted ? 'tth-row--anon' : null,
        ]"
      >
        <MkAvatar
          :src="!entry.deleted ? entry.author?.avatar_url || null : null"
          :name="entry.deleted ? '?' : entry.author?.display_name || '?'"
          :size="32"
          :tier="(!entry.deleted && entry.author?.tier) || 'bronze'"
          class="tth-avatar"
        />

        <div class="tth-bubble">
          <div class="tth-meta">
            <span class="tth-name">
              {{
                entry.deleted
                  ? $t('portal.common.deletedUser')
                  : entry.author?.display_name || $t('portal.tickets.user')
              }}
            </span>
            <span v-if="!entry.deleted && entry.isAdmin" class="tth-role-pill">
              {{ $t('portal.tickets.thread.adminBadge') }}
            </span>
            <span class="tth-time" :title="formatAbsolute(entry.created_at)">
              {{ formatRelative(entry.created_at) }}
            </span>
          </div>
          <p class="tth-content">{{ entry.content }}</p>
        </div>
      </li>
    </ol>

    <!-- Status footer when the ticket reaches a terminal state -->
    <div
      v-if="ticket.status === 'resolved' || ticket.status === 'closed'"
      class="tth-status-footer"
      :class="`tth-status-footer--${ticket.status}`"
    >
      {{ $t(`portal.tickets.thread.statusFooter.${ticket.status}`) }}
    </div>

    <!-- Reply form -->
    <form v-if="ticket.status !== 'closed'" class="tth-form" @submit.prevent="onSubmit">
      <textarea
        v-model="text"
        class="tth-input"
        rows="3"
        maxlength="2000"
        :placeholder="$t('portal.tickets.replyPlaceholder')"
      />
      <button type="submit" class="tth-btn" :disabled="!text.trim() || submitting">
        {{ $t('portal.tickets.sendReply') }}
      </button>
    </form>
  </section>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { MessageSquare } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'

import '@/assets/styles/portal/ticket-thread.css'

const props = defineProps({
  ticket: { type: Object, required: true },
})

const emit = defineEmits(['reply'])

const { t } = useI18n()
const { profile } = usePortalAuth()

const text = ref('')
const submitting = ref(false)
const listEl = ref(null)

const myUserId = computed(() => profile.value?.user_id ?? null)

/**
 * Unified entry list — the ticket description is rendered as the first
 * bubble so the thread reads as one continuous conversation, with the
 * requester's original message at the top and replies stacked below it.
 */
const entries = computed(() => {
  const tk = props.ticket
  const list = []
  if (tk.description) {
    list.push({
      key: `t-${tk.id}`,
      content: tk.description,
      created_at: tk.created_at,
      author: tk.requester,
      isAdmin: tk.requester?.role === 'admin',
      mine: tk.requester?.user_id === myUserId.value,
      deleted: !!tk.requester_deleted,
    })
  }
  for (const r of tk.replies || []) {
    list.push({
      key: `r-${r.id}`,
      content: r.content,
      created_at: r.created_at,
      author: r.author,
      isAdmin: r.author?.role === 'admin',
      mine: r.author?.user_id === myUserId.value,
      deleted: !!r.author_deleted,
    })
  }
  return list
})

watch(
  () => props.ticket?.replies?.length,
  async () => {
    // Auto-scroll to the newest bubble whenever the reply count grows.
    await nextTick()
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  },
)

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

function formatAbsolute(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

async function onSubmit() {
  const value = text.value.trim()
  if (!value) return
  submitting.value = true
  try {
    await emit('reply', value)
    text.value = ''
  } finally {
    submitting.value = false
  }
}
</script>
